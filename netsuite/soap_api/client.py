import logging
import re
from contextlib import contextmanager
from datetime import datetime
from functools import cached_property
from typing import Dict, List, Optional, Sequence

from ..config import Config
from . import helpers, passport, zeep
from .decorators import WebServiceCall
from .transports import AsyncNetSuiteTransport

logger = logging.getLogger(__name__)

__all__ = ("NetSuiteSoapApi",)


class NetSuiteSoapApi:
    version = "2021.1.0"
    wsdl_url_tmpl = "https://{account_slug}.suitetalk.api.netsuite.com/wsdl/v{underscored_version}/netsuite.wsdl"

    def __init__(
        self,
        config: Config,
        *,
        version: Optional[str] = None,
        wsdl_url: Optional[str] = None,
        cache: Optional[zeep.cache.Base] = None,
    ) -> None:
        self._ensure_required_dependencies()
        if version is not None:
            assert re.match(r"\d+\.\d+\.\d+", version)
            self.version = version
        self.config: Config = config
        self._wsdl_url: Optional[str] = wsdl_url
        self._cache: Optional[zeep.cache.Base] = cache
        self._client: Optional[zeep.client.AsyncClient] = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.hostname}({self.version})>"

    async def __aenter__(self):
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type=None, exc_value=None, traceback=None) -> None:
        await self.client.__aexit__(
            exc_type=exc_type, exc_value=exc_value, traceback=traceback
        )
        # Connection is now closed by zeep. Generate a new one
        self._client = self._generate_client()

    @property
    def wsdl_url(self) -> str:
        if self._wsdl_url is None:
            self._wsdl_url = self._generate_wsdl_url()
        return self._wsdl_url

    @property
    def cache(self) -> zeep.cache.Base:
        if self._cache is None:
            self._cache = self._generate_cache()
        return self._cache

    @property
    def client(self) -> zeep.client.AsyncClient:
        if self._client is None:
            self._client = self._generate_client()
        return self._client

    @property
    def transport(self):
        return self.client.transport

    @cached_property
    def hostname(self) -> str:
        return self.wsdl_url.replace("https://", "").partition("/")[0]

    @property
    def service(self) -> zeep.client.ServiceProxy:
        return self.client.service

    @property
    def underscored_version(self) -> str:
        return self.version.replace(".", "_")

    @property
    def underscored_version_no_micro(self) -> str:
        return self.underscored_version.rpartition("_")[0]

    def _generate_wsdl_url(self) -> str:
        return self.wsdl_url_tmpl.format(
            underscored_version=self.underscored_version,
            account_slug=self.config.account_slugified,
        )

    def _generate_cache(self) -> zeep.cache.Base:
        return zeep.cache.SqliteCache(timeout=60 * 60 * 24 * 365)

    def _generate_transport(self) -> zeep.transports.AsyncTransport:
        return AsyncNetSuiteTransport(
            self.wsdl_url,
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

    def _generate_client(self) -> zeep.client.AsyncClient:
        return zeep.client.AsyncClient(
            self.wsdl_url,
            transport=self._generate_transport(),
        )

    def _get_namespace(self, name: str, sub_namespace: str) -> str:
        return "urn:{name}_{version}.{sub_namespace}.webservices.netsuite.com".format(
            name=name,
            version=self.underscored_version_no_micro,
            sub_namespace=sub_namespace,
        )

    def _type_factory(self, name: str, sub_namespace: str) -> zeep.client.Factory:
        return self.client.type_factory(self._get_namespace(name, sub_namespace))

    @classmethod
    def _ensure_required_dependencies(cls):
        if not cls._has_required_dependencies():
            raise RuntimeError(
                "Missing required dependencies for SOAP Web Services API support. "
                "Install with `pip install netsuite[soap_api]`"
            )

    @classmethod
    def _has_required_dependencies(cls) -> bool:
        return zeep.ZEEP_INSTALLED

    @cached_property
    def Core(self) -> zeep.client.Factory:
        return self._type_factory("core", "platform")

    @cached_property
    def CoreTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.core", "platform")

    @cached_property
    def FaultsTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.faults", "platform")

    @cached_property
    def Faults(self) -> zeep.client.Factory:
        return self._type_factory("faults", "platform")

    @cached_property
    def Messages(self) -> zeep.client.Factory:
        return self._type_factory("messages", "platform")

    @cached_property
    def Common(self) -> zeep.client.Factory:
        return self._type_factory("common", "platform")

    @cached_property
    def CommonTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.common", "platform")

    @cached_property
    def Scheduling(self) -> zeep.client.Factory:
        return self._type_factory("scheduling", "activities")

    @cached_property
    def SchedulingTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.scheduling", "activities")

    @cached_property
    def Communication(self) -> zeep.client.Factory:
        return self._type_factory("communication", "general")

    @cached_property
    def CommunicationTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.communication", "general")

    @cached_property
    def Filecabinet(self) -> zeep.client.Factory:
        return self._type_factory("filecabinet", "documents")

    @cached_property
    def FilecabinetTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.filecabinet", "documents")

    @cached_property
    def Relationships(self) -> zeep.client.Factory:
        return self._type_factory("relationships", "lists")

    @cached_property
    def RelationshipsTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.relationships", "lists")

    @cached_property
    def Support(self) -> zeep.client.Factory:
        return self._type_factory("support", "lists")

    @cached_property
    def SupportTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.support", "lists")

    @cached_property
    def Accounting(self) -> zeep.client.Factory:
        return self._type_factory("accounting", "lists")

    @cached_property
    def AccountingTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.accounting", "lists")

    @cached_property
    def Sales(self) -> zeep.client.Factory:
        return self._type_factory("sales", "transactions")

    @cached_property
    def SalesTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.sales", "transactions")

    @cached_property
    def Purchases(self) -> zeep.client.Factory:
        return self._type_factory("purchases", "transactions")

    @cached_property
    def PurchasesTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.purchases", "transactions")

    @cached_property
    def Customers(self) -> zeep.client.Factory:
        return self._type_factory("customers", "transactions")

    @cached_property
    def CustomersTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.customers", "transactions")

    @cached_property
    def Financial(self) -> zeep.client.Factory:
        return self._type_factory("financial", "transactions")

    @cached_property
    def FinancialTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.financial", "transactions")

    @cached_property
    def Bank(self) -> zeep.client.Factory:
        return self._type_factory("bank", "transactions")

    @cached_property
    def BankTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.bank", "transactions")

    @cached_property
    def Inventory(self) -> zeep.client.Factory:
        return self._type_factory("inventory", "transactions")

    @cached_property
    def InventoryTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.inventory", "transactions")

    @cached_property
    def General(self) -> zeep.client.Factory:
        return self._type_factory("general", "transactions")

    @cached_property
    def Customization(self) -> zeep.client.Factory:
        return self._type_factory("customization", "setup")

    @cached_property
    def CustomizationTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.customization", "setup")

    @cached_property
    def Employees(self) -> zeep.client.Factory:
        return self._type_factory("employees", "lists")

    @cached_property
    def EmployeesTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.employees", "lists")

    @cached_property
    def Website(self) -> zeep.client.Factory:
        return self._type_factory("website", "lists")

    @cached_property
    def WebsiteTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.website", "lists")

    @cached_property
    def EmployeesTransactions(self) -> zeep.client.Factory:
        return self._type_factory("employees", "transactions")

    @cached_property
    def EmployeesTransactionsTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.employees", "transactions")

    @cached_property
    def Marketing(self) -> zeep.client.Factory:
        return self._type_factory("marketing", "lists")

    @cached_property
    def MarketingTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.marketing", "lists")

    @cached_property
    def DemandPlanning(self) -> zeep.client.Factory:
        return self._type_factory("demandplanning", "transactions")

    @cached_property
    def DemandPlanningTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.demandplanning", "transactions")

    @cached_property
    def SupplyChain(self) -> zeep.client.Factory:
        return self._type_factory("supplychain", "lists")

    @cached_property
    def SupplyChainTypes(self) -> zeep.client.Factory:
        return self._type_factory("types.supplychain", "lists")

    async def request(
        self, service_name: str, *args, additionalHeaders: Optional[dict] = None, **kw
    ):
        """
        Make a web service request to NetSuite

        Args:
            service_name:
                The NetSuite service to call
        Returns:
            The response from NetSuite
        """
        svc = getattr(self.service, service_name)
        headers = self.generate_passport()
        if additionalHeaders:
            headers.update(additionalHeaders)
        return await svc(*args, _soapheaders=headers, **kw)

    @WebServiceCall(
        "body.readResponseList.readResponse",
        extract=lambda resp: [r["record"] for r in resp],
    )
    async def getList(
        self,
        recordType: str,
        *,
        internalIds: Optional[Sequence[int]] = None,
        externalIds: Optional[Sequence[str]] = None,
    ) -> List[zeep.xsd.CompoundValue]:
        """Get a list of records"""
        if internalIds is None:
            internalIds = []
        else:
            internalIds = list(internalIds)
        if externalIds is None:
            externalIds = []
        else:
            externalIds = list(externalIds)

        if len(internalIds) + len(externalIds) == 0:
            return []

        return await self.request(
            "getList",
            self.Messages.GetListRequest(
                baseRef=[
                    self.Core.RecordRef(
                        type=recordType,
                        internalId=internalId,
                    )
                    for internalId in internalIds
                ]
                + [
                    self.Core.RecordRef(
                        type=recordType,
                        externalId=externalId,
                    )
                    for externalId in externalIds
                ],
            ),
        )

    @WebServiceCall(
        "body.readResponse",
        extract=lambda resp: resp["record"],
    )
    async def get(
        self,
        recordType: str,
        *,
        internalId: Optional[int] = None,
        externalId: Optional[str] = None,
    ) -> zeep.xsd.CompoundValue:
        """Get a single record"""
        if len([v for v in (internalId, externalId) if v is not None]) != 1:
            raise ValueError("Specify either `internalId` or `externalId`")

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

        return await self.request("get", baseRef=record_ref)

    @WebServiceCall(
        "body.getAllResult",
        extract=lambda resp: resp["recordList"]["record"],
    )
    async def getAll(self, recordType: str) -> List[zeep.xsd.CompoundValue]:
        """Get all records of a given type."""
        return await self.request(
            "getAll",
            record=self.Core.GetAllRecord(
                recordType=recordType,
            ),
        )

    @WebServiceCall(
        "body.writeResponse",
        extract=lambda resp: resp["baseRef"],
    )
    async def add(self, record: zeep.xsd.CompoundValue) -> zeep.xsd.CompoundValue:
        """Insert a single record."""
        return await self.request("add", record=record)

    @WebServiceCall(
        "body.writeResponse",
        extract=lambda resp: resp["baseRef"],
    )
    async def update(self, record: zeep.xsd.CompoundValue) -> zeep.xsd.CompoundValue:
        """Insert a single record."""
        return await self.request("update", record=record)

    @WebServiceCall(
        "body.writeResponse",
        extract=lambda resp: resp["baseRef"],
    )
    async def upsert(self, record: zeep.xsd.CompoundValue) -> zeep.xsd.CompoundValue:
        """Upsert a single record."""
        return await self.request("upsert", record=record)

    @WebServiceCall(
        "body.searchResult",
        extract=lambda resp: resp["recordList"]["record"],
    )
    async def search(
        self, record: zeep.xsd.CompoundValue, additionalHeaders: Optional[dict] = None
    ) -> List[zeep.xsd.CompoundValue]:
        """Search records"""
        return await self.request(
            "search", searchRecord=record, additionalHeaders=additionalHeaders
        )

    @WebServiceCall(
        "body.searchResult",
        extract=lambda resp: resp["recordList"]["record"],
    )
    async def searchMoreWithId(
        self, searchId: str, pageIndex: int
    ) -> List[zeep.xsd.CompoundValue]:
        """Search records with pagination"""
        return await self.request(
            "searchMoreWithId", searchId=searchId, pageIndex=pageIndex
        )

    @WebServiceCall(
        "body.writeResponseList",
        extract=lambda resp: [record["baseRef"] for record in resp],
    )
    async def upsertList(
        self, records: List[zeep.xsd.CompoundValue]
    ) -> List[zeep.xsd.CompoundValue]:
        """Upsert a list of records."""
        return await self.request("upsertList", record=records)

    @WebServiceCall(
        "body.getItemAvailabilityResult",
        extract=lambda resp: resp["itemAvailabilityList"]["itemAvailability"],
        default=[],
    )
    async def getItemAvailability(
        self,
        *,
        internalIds: Optional[Sequence[int]] = None,
        externalIds: Optional[Sequence[str]] = None,
        lastQtyAvailableChange: Optional[datetime] = None,
    ) -> List[Dict]:
        if internalIds is None:
            internalIds = []
        else:
            internalIds = list(internalIds)
        if externalIds is None:
            externalIds = []
        else:
            externalIds = list(externalIds)

        if len(internalIds) + len(externalIds) == 0:
            return []

        item_filters = [
            {"type": "inventoryItem", "internalId": internalId}
            for internalId in internalIds
        ] + [
            {"type": "inventoryItem", "externalId": externalId}
            for externalId in externalIds
        ]

        return await self.request(
            "getItemAvailability",
            itemAvailabilityFilter=[
                {
                    "item": {"recordRef": item_filters},
                    "lastQtyAvailableChange": lastQtyAvailableChange,
                }
            ],
        )
