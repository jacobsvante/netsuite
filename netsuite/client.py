import logging
import re
import warnings
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Sequence, Union, Optional

import requests
import zeep
from zeep.cache import SqliteCache
from zeep.xsd.valueobjects import CompoundValue

from . import constants, helpers, passport
from .config import Config
from .restlet import NetsuiteRestlet
from .util import cached_property, Capturing

logger = logging.getLogger(__name__)


class NetsuiteResponseError(Exception):
    """Raised when a Netsuite result was marked as unsuccessful"""


class NoSuchTypeError(Exception):
    """Raised when attempting to fetch a factory or get a factory name for an undefined type."""


def WebServiceCall(
    path: str = None,
    extract: Callable = None,
    *,
    default: Any = constants.NOT_SET,
) -> Callable:
    """
    Decorator for NetSuite methods returning SOAP responses

    Args:
        path:
            A dot-separated path for specifying where relevant data resides (where the `status` attribute is set)
        extract:
            A function to extract data from response before returning it.
        default:
            If the existing path does not exist in response, return this
            instead.

    Returns:
        Decorator to use on `NetSuite` web service methods
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(self, *args, **kw):
            response = fn(self, *args, **kw)

            if path is not None:
                for part in path.split('.'):
                    try:
                        response = getattr(response, part)
                    except AttributeError:
                        if default is constants.NOT_SET:
                            raise
                        else:
                            return default

            try:
                response_status = response['status']
            except TypeError:
                response_status = None
                for record in response:
                    # NOTE: Status is set on each returned record for lists,
                    #       really strange...
                    response_status = record['status']
                    break

            is_success = response_status['isSuccess']

            if not is_success:
                response_detail = response_status['statusDetail']
                raise NetsuiteResponseError(response_detail)

            if extract is not None:
                response = extract(response)

            return response
        return wrapper
    return decorator


class NetSuite:
    version = '2018.1.0'
    wsdl_url_tmpl = 'https://{account_id}.suitetalk.api.netsuite.com/wsdl/v{underscored_version}/netsuite.wsdl'

    def __repr__(self) -> str:
        return f'<NetSuite {self.hostname}({self.version})>'

    def __init__(
        self,
        config: Union[Config, Dict],
        *,
        version: str = None,
        wsdl_url: str = None,
        cache: zeep.cache.Base = None,
        session: requests.Session = None,
        sandbox: bool = None
    ) -> None:

        if sandbox is not None:
            warnings.warn(
                'The `sandbox` flag has been deprecated and no longer has '
                'any effect. Please locate the correct account ID for your '
                'sandbox instead (usually `_SB1`)',
                DeprecationWarning,
            )

        if version is not None:
            assert re.match(r'\d+\.\d+\.\d+', version)
            self.version = version

        self.__config = self._make_config(config)
        self.__wsdl_url = wsdl_url
        self.__cache = cache
        self.__session = session
        self.__restlet = NetsuiteRestlet(self.__config)

    @property
    def restlet(self):
        return self.__restlet

    @cached_property
    def wsdl_url(self) -> str:
        return self.__wsdl_url or self._generate_wsdl_url()

    @cached_property
    def cache(self) -> zeep.cache.Base:
        return self.__cache or self._generate_cache()

    @cached_property
    def session(self) -> requests.Session:
        return self.__session or self._generate_session()

    @cached_property
    def client(self) -> zeep.Client:
        return self._generate_client()

    @cached_property
    def transport(self):
        return self._generate_transport()

    @property
    def config(self) -> Config:
        return self.__config

    @cached_property
    def hostname(self) -> str:
        return self.wsdl_url.replace('https://', '').partition('/')[0]

    @property
    def service(self) -> zeep.client.ServiceProxy:
        return self.client.service

    def _make_config(
        self,
        values_obj: Dict
    ) -> Config:
        if isinstance(values_obj, Config):
            return values_obj
        return Config(**values_obj)

    @property
    def underscored_version(self) -> str:
        return self.version.replace('.', '_')

    @property
    def underscored_version_no_micro(self) -> str:
        return self.underscored_version.rpartition('_')[0]

    def _generate_wsdl_url(self) -> str:
        return self.wsdl_url_tmpl.format(
            underscored_version=self.underscored_version,
            # https://followingnetsuite.wordpress.com/2018/10/18/suitetalk-sandbox-urls-addendum/
            account_id=self.config.account.lower().replace('_', '-'),
        )

    def _generate_cache(self) -> zeep.cache.Base:
        return SqliteCache(timeout=60 * 60 * 24 * 365)

    def _generate_session(self) -> requests.Session:
        return requests.Session()

    def _generate_transport(self) -> zeep.transports.Transport:
        return zeep.transports.Transport(
            session=self.session,
            cache=self.cache,
        )

    def generate_passport(self) -> Dict:
        return passport.make(self, self.config)

    def to_builtin(self, obj, *args, **kw):
        """Turn zeep XML object into python built-in data structures"""
        return helpers.to_builtin(obj, *args, **kw)

    @contextmanager
    def with_timeout(self, timeout: int):
        """Run SuiteTalk operation with the specified timeout"""
        with self.transport.settings(timeout=timeout):
            yield

    @staticmethod
    def _set_default_soapheaders(
        client: zeep.Client,
        preferences: dict = None
    ) -> None:
        client.set_default_soapheaders({
            # https://netsuite.custhelp.com/app/answers/detail/a_id/40934
            # (you need to be logged in to SuiteAnswers for this link to work)
            # 'preferences': {
            #     'warningAsError': True/False,
            #     'disableMandatoryCustomFieldValidation': True/False,
            #     'disableSystemNotesForCustomFields': True/False,
            #     'ignoreReadOnlyFields': True/False,
            #     'runServerSuiteScriptAndTriggerWorkflows': True/False,
            # },
        })

    def _generate_client(self) -> zeep.Client:
        client = zeep.Client(
            self.wsdl_url,
            transport=self.transport,
        )
        self._set_default_soapheaders(
            client,
            preferences=self.config.preferences,
        )
        return client

    def _get_namespace(self, name: str, sub_namespace: str) -> str:
        return (
            'urn:{name}_{version}.{sub_namespace}.webservices.netsuite.com'
            .format(
                name=name,
                version=self.underscored_version_no_micro,
                sub_namespace=sub_namespace,
            )
        )

    def _type_factory(
        self,
        name: str,
        sub_namespace: str
    ) -> zeep.client.Factory:
        return self.client.type_factory(
            self._get_namespace(name, sub_namespace)
        )

    @cached_property
    def types_dump(self) -> List[str]:
        """
        Returns a list of strings with each item describing a different type defined in the service WSDL. This is a
        convenience method that snags the stdout of zeep.client.wsdl.dump(). The output is very verbose.
        :return: list of string with each item describing a different type in the service WSDL.

        Example:

        types_list = client.types_dump
        """
        with Capturing() as dump:
            self.client.wsdl.dump()
        starting_point = dump.index('Global types:') + 1
        return [line.strip() for line in dump[starting_point:]]

    def search_types(self, query: str) -> List[str]:
        """
        Returns all (case insensitive) matches to types listed in the WSDL.
        :param query: string to search for in WSDL types definitions
        :return: list of all types defined in the WSDL that at least partially match the query string

        Example:

        type_definitions_containing_substring_vendor = client.search_types('Vendor')
        """
        query = query.lower()
        # boolean, integer, float, etc.
        basic_types = [type_def for type_def in self.types_dump
                       if 'xsd:' in type_def and query in type_def.lower() and '(' not in type_def]
        # VendorSearch, VendorSearchBasic, etc.
        wsdl_types = [type_def for type_def in self.types_dump if '(' in type_def and query in type_def.split('(')[0].lower()]
        return basic_types + wsdl_types

    def search_type_args(self, query: str) -> List[str]:
        """
        Returns all (case insensitive) matches where query is a substring of an argument to a type constructor defined
        in the WSDL.
        :param query: string to search for in WSDL types definitions arguments
        :return: list of all types defined in the WSDL that have at least one argument matching the query string

        Example:

        type_definitions_with_vendor_in_arg_names = client.search_type_args('Vendor')
        """
        query = query.lower()
        return [type_def for type_def in self.types_dump if '(' in type_def and query in type_def.split('(')[1].lower()]

    def get_type(self, type_name: str) -> Optional[str]:
        """
        Returns type definition matching (case sensitive) type_name from WSDL.
        :param type_name: case sensitive string matching the name of a type defined in the WSDL.
        :return:

        Example:

        client.get_type('VendorSearch')

        # `ns13:VendorSearch(basic: ns5:VendorSearchBasic, **)`
        """
        for type_def in self.types_dump:
            if f'xsd:{type_name}' in type_def or f':{type_name}(' in type_def:
                return type_def

    def get_type_factory_name(self, type_name: str) -> str:
        """
        Returns the name of the type factory containing this particular type.
        :param type_name: name of type that we want to be able to generate
        :return: name of factory capable of generating type_name objects.

        Example:

        client.get_type_factory_name('VendorSearch')

        #'Relationships'
        """
        type_description = self.get_type(type_name)
        if not type_description:
            raise NoSuchTypeError(f'Type {type_name} not defined in the WSDL.')
        namespace_index = int(type_description.split(':')[0][2:])
        return constants.FACTORIES[namespace_index]

    def get_type_class(self, type_name: str):
        """
        Returns the Class object (practically, a type constructor) corresponding to the case-sensitive type_name
        :param type_name: name of type class
        :return: Class object corresponding to the case-sensitive type_name

        Example:

        VendorSearch = client.get_type_class('VendorSearch')
        vendor_search_obj = VendorSearch(*args, **kwargs)
        """
        type_description = self.get_type(type_name)
        if not type_description:
            raise NoSuchTypeError(f'Type {type_name} not defined in the WSDL.')
        namespace_index = int(type_description.split(':')[0][2:])
        return getattr(self._type_factory(*constants.URN_AS_ARGS[namespace_index]), type_name)

    @cached_property
    def Core(self) -> zeep.client.Factory:
        return self._type_factory('core', 'platform')

    @cached_property
    def CoreTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.core', 'platform')

    @cached_property
    def FaultsTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.faults', 'platform')

    @cached_property
    def Faults(self) -> zeep.client.Factory:
        return self._type_factory('faults', 'platform')

    @cached_property
    def Messages(self) -> zeep.client.Factory:
        return self._type_factory('messages', 'platform')

    @cached_property
    def Common(self) -> zeep.client.Factory:
        return self._type_factory('common', 'platform')

    @cached_property
    def CommonTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.common', 'platform')

    @cached_property
    def Scheduling(self) -> zeep.client.Factory:
        return self._type_factory('scheduling', 'activities')

    @cached_property
    def SchedulingTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.scheduling', 'activities')

    @cached_property
    def Communication(self) -> zeep.client.Factory:
        return self._type_factory('communication', 'general')

    @cached_property
    def CommunicationTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.communication', 'general')

    @cached_property
    def Filecabinet(self) -> zeep.client.Factory:
        return self._type_factory('filecabinet', 'documents')

    @cached_property
    def FilecabinetTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.filecabinet', 'documents')

    @cached_property
    def Relationships(self) -> zeep.client.Factory:
        return self._type_factory('relationships', 'lists')

    @cached_property
    def RelationshipsTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.relationships', 'lists')

    @cached_property
    def Support(self) -> zeep.client.Factory:
        return self._type_factory('support', 'lists')

    @cached_property
    def SupportTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.support', 'lists')

    @cached_property
    def Accounting(self) -> zeep.client.Factory:
        return self._type_factory('accounting', 'lists')

    @cached_property
    def AccountingTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.accounting', 'lists')

    @cached_property
    def Sales(self) -> zeep.client.Factory:
        return self._type_factory('sales', 'transactions')

    @cached_property
    def SalesTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.sales', 'transactions')

    @cached_property
    def Purchases(self) -> zeep.client.Factory:
        return self._type_factory('purchases', 'transactions')

    @cached_property
    def PurchasesTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.purchases', 'transactions')

    @cached_property
    def Customers(self) -> zeep.client.Factory:
        return self._type_factory('customers', 'transactions')

    @cached_property
    def CustomersTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.customers', 'transactions')

    @cached_property
    def Financial(self) -> zeep.client.Factory:
        return self._type_factory('financial', 'transactions')

    @cached_property
    def FinancialTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.financial', 'transactions')

    @cached_property
    def Bank(self) -> zeep.client.Factory:
        return self._type_factory('bank', 'transactions')

    @cached_property
    def BankTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.bank', 'transactions')

    @cached_property
    def Inventory(self) -> zeep.client.Factory:
        return self._type_factory('inventory', 'transactions')

    @cached_property
    def InventoryTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.inventory', 'transactions')

    @cached_property
    def General(self) -> zeep.client.Factory:
        return self._type_factory('general', 'transactions')

    @cached_property
    def Customization(self) -> zeep.client.Factory:
        return self._type_factory('customization', 'setup')

    @cached_property
    def CustomizationTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.customization', 'setup')

    @cached_property
    def Employees(self) -> zeep.client.Factory:
        return self._type_factory('employees', 'lists')

    @cached_property
    def EmployeesTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.employees', 'lists')

    @cached_property
    def Website(self) -> zeep.client.Factory:
        return self._type_factory('website', 'lists')

    @cached_property
    def WebsiteTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.website', 'lists')

    @cached_property
    def EmployeesTransactions(self) -> zeep.client.Factory:
        return self._type_factory('employees', 'transactions')

    @cached_property
    def EmployeesTransactionsTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.employees', 'transactions')

    @cached_property
    def Marketing(self) -> zeep.client.Factory:
        return self._type_factory('marketing', 'lists')

    @cached_property
    def MarketingTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.marketing', 'lists')

    @cached_property
    def DemandPlanning(self) -> zeep.client.Factory:
        return self._type_factory('demandplanning', 'transactions')

    @cached_property
    def DemandPlanningTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.demandplanning', 'transactions')

    @cached_property
    def SupplyChain(self) -> zeep.client.Factory:
        return self._type_factory('supplychain', 'lists')

    @cached_property
    def SupplyChainTypes(self) -> zeep.client.Factory:
        return self._type_factory('types.supplychain', 'lists')

    def request(
        self,
        service_name: str,
        *args,
        **kw
    ) -> zeep.xsd.ComplexType:
        """
        Make a web service request to NetSuite

        Args:
            service_name:
                The NetSuite service to call
        Returns:
            The response from NetSuite
        """
        svc = getattr(self.service, service_name)
        return svc(*args, _soapheaders=self.generate_passport(), **kw)

    @WebServiceCall(
        'body.readResponseList.readResponse',
        extract=lambda resp: [r['record'] for r in resp]
    )
    def getList(
        self,
        recordType: str,
        *,
        internalIds: Sequence[int] = (),
        externalIds: Sequence[str] = ()
    ) -> List[CompoundValue]:
        """Get a list of records"""

        if len(list(internalIds) + list(externalIds)) == 0:
            raise ValueError('Please specify `internalId` and/or `externalId`')

        return self.request(
            'getList',
            self.Messages.GetListRequest(
                baseRef=[
                    self.Core.RecordRef(
                        type=recordType,
                        internalId=internalId,
                    ) for internalId in internalIds
                ] + [
                    self.Core.RecordRef(
                        type=recordType,
                        externalId=externalId,
                    ) for externalId in externalIds
                ],
            )
        )

    @WebServiceCall(
        'body.readResponse',
        extract=lambda resp: resp['record'],
    )
    def get(
        self,
        recordType: str,
        *,
        internalId: int = None,
        externalId: str = None
    ) -> CompoundValue:
        """Get a single record"""
        if len([v for v in (internalId, externalId) if v is not None]) != 1:
            raise ValueError('Specify either `internalId` or `externalId`')

        if internalId:
            record_ref = self.Core.RecordRef(
                type=recordType,
                internalId=internalId,
            )
        else:
            record_ref = self.Core.RecordRef(
                type=recordType,
                externalId=externalId,
            )

        return self.request('get', baseRef=record_ref)

    @WebServiceCall(
        'body.getAllResult',
        extract=lambda resp: resp['recordList']['record'],
    )
    def getAll(self, recordType: str) -> List[CompoundValue]:
        """Get all records of a given type."""
        return self.request(
            'getAll',
            record=self.Core.GetAllRecord(
                recordType=recordType,
            ),
        )

    @WebServiceCall(
        'body.writeResponse',
        extract=lambda resp: resp['baseRef'],
    )
    def add(self, record: CompoundValue) -> CompoundValue:
        """
        Insert a single record. It is recommended that you use a consistent convention for externalId to facilitate
        record reference via get and upsert methods.

        example:
            InventoryItem = client.get_type_class('InventoryItem') # InventoryItem constructor
            RecordRef = client.get_type_class('RecordRef') # RecordRef constructor

            tax_schedule = RecordRef(internalId=1) # corresponds to default tax_schedule
            item_dict = {"itemId": "1", "displayName": "Red", "taxSchedule": tax_schedule}
            item = InventoryItem(**item_dict, externalId=f"{item_dict['itemId']}-{item_dict['displayName']}")

            client.add(item)

        :param record: RecordRef{name: str, type: str, internalId: str, externalId: str}
        :return: RecordRef
        """
        return self.request('add', record=record)

    @WebServiceCall(
        'body.writeResponse',
        extract=lambda resp: resp['baseRef'],
    )
    def update(self, record: CompoundValue) -> CompoundValue:
        """
        Update a single record.

        example:

            InventoryItem = client.get_type_class('InventoryItem') # InventoryItem constructor
            RecordRef = client.get_type_class('RecordRef') # RecordRef constructor

            tax_schedule = RecordRef(internalId=1) # corresponds to default tax_schedule
            item_dict = {"itemId": "1", "displayName": "Red", "taxSchedule": tax_schedule}
            item = InventoryItem(**item_dict, externalId=f"{item_dict['itemId']}-{item_dict['displayName']}")
            item.displayName = "Red-Different-Now"

            client.update(item)

        :param record: RecordRef{name: str, type: str, internalId: str, externalId: str}
        :return: RecordRef
        """
        return self.request('update', record=record)

    @WebServiceCall(
        'body.writeResponse',
        extract=lambda resp: resp['baseRef'],
    )
    def upsert(self, record: CompoundValue) -> CompoundValue:
        """
        Upsert a single record; method requires externalId to be defined for RecordRef. If externalId exists,
        the record corresponding to that externalId is updated. Otherwise, a new one will be created.

        example:
            InventoryItem = client.get_type_class('InventoryItem') # InventoryItem constructor
            RecordRef = client.get_type_class('RecordRef') # RecordRef constructor

            tax_schedule = RecordRef(internalId=1) # corresponds to default tax_schedule
            item_dict = {"itemId": "1", "displayName": "Red", "taxSchedule": tax_schedule}
            item = InventoryItem(**item_dict, externalId=f"{item_dict['itemId']}-{item_dict['displayName']}")

            client.upsert(item)

        :param record: RecordRef{name: str, type: str, internalId: str, externalId: str}
        :return: RecordRef
        """
        return self.request('upsert', record=record)

    @WebServiceCall(
        'body.writeResponse',
        extract=lambda resp: resp,
    )
    def delete(self, record: CompoundValue, deletion_reason: CompoundValue=None) -> CompoundValue:

        """
        Delete a single record.

        https://<environmentid>.app.netsuite.com/app/help/helpcenter.nl?fid=section_N3486046.html
        NetSuite.delete(RecordRef, RecordRef<DeletionReason>)

        ex:
            record_dict = { 'name': 'Green', 'internalId': '382', 'externalId': None, 'type': 'inventoryItem' }
            RecordRef = client.get_type_class('RecordRef') # RecordRef constructor
            record = RecordRef(**record_dict)

            client.delete(record, None) # DeletionReason can be None

        :param record: RecordRef with internalId or externalId and type specified for targeted record deletion
        :param deletion_reason: RecordRef of DeletionReason, which contains a reason code and description
            that can be managed in NetSuite UI
        :return: WriteResponse<DeleteResponse{status: {statusDetail: list, isSuccess: bool}, baseRef: RecordRef}>
        """
        return self.request('delete', record, deletion_reason)


    @WebServiceCall(
        'body.writeResponse',
        extract=lambda resp: resp,
    )
    def deleteList(self, records: List[CompoundValue], deletion_reason: List[CompoundValue]) -> CompoundValue:
        """
        Delete a list of records.

        :param records: a list of RecordRef objects corresponding to items to be deleted.
        :param deletion_reason: RecordRef of DeletionReason, which contains a reason code and description
            that can be managed in NetSuite UI
        :return: List[WriteResponse<DeleteResponse{status: {statusDetail: list, isSuccess: bool}, baseRef: RecordRef}]
        """

        logger.WARNING("deleteList implementation is not stable, expect errors.")

        return self.request('deleteList', records, deletion_reason)

    @WebServiceCall(
        'body.searchResult',
        extract=lambda resp: resp['recordList']['record'],
    )
    def search(self, record: CompoundValue) -> List[CompoundValue]:
        """Search records"""
        return self.request('search', searchRecord=record)

    @WebServiceCall(
        'body.writeResponseList',
        extract=lambda resp: resp,
    )
    def upsertList(self, records: List[CompoundValue]) -> List[CompoundValue]:
        """

        :param records: list of RecordRef objects corresponding to items to be deleted
        :return: List[WriteResponse<DeleteResponse{status: {statusDetail: list, isSuccess: bool}, baseRef: RecordRef}>]
        """
        return self.request('upsertList', record=records)

    @WebServiceCall(
        'body.getItemAvailabilityResult',
        extract=lambda resp: resp['itemAvailabilityList']['itemAvailability'],
        default=[]
    )
    def getItemAvailability(
        self,
        *,
        internalIds: Sequence[int] = (),
        externalIds: Sequence[str] = (),
        lastQtyAvailableChange: datetime = None
    ) -> List[Dict]:
        if len(list(internalIds) + list(externalIds)) == 0:
            raise ValueError('Please specify `internalId` and/or `externalId`')

        item_filters = [
            {'type': 'inventoryItem', 'internalId': internalId}
            for internalId in internalIds
        ] + [
            {'type': 'inventoryItem', 'externalId': externalId}
            for externalId in externalIds
        ]

        return self.request(
            'getItemAvailability',
            itemAvailabilityFilter=[{
                'item': {'recordRef': item_filters},
                'lastQtyAvailableChange': lastQtyAvailableChange
            }],
        )
