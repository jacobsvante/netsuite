import logging
import re
from functools import cached_property
from typing import Any, AsyncIterator, Dict, Optional, Sequence, Union

from . import json, rest_api_base
from .config import Config
from .exceptions import NetsuiteAPIRequestError

logger = logging.getLogger(__name__)

__all__ = ("NetSuiteRestApi",)

# Custom media types introduced for the 2026.1 REST web services
# operations. Batch uses a `collection` content type; create-form and
# selectOptions select their behaviour through the `Accept` header.
_COLLECTION_MEDIA_TYPE = "application/vnd.oracle.resource+json; type=collection"
_CREATE_FORM_MEDIA_TYPE = "application/vnd.oracle.resource+json; type=create-form"
_SELECT_OPTIONS_MEDIA_TYPE = "application/vnd.oracle.resource+json; type=select-options"

# Batch add/update/upsert verbs (GET/DELETE batches go through the normal
# get()/delete() with an `ids` param instead).
_BATCH_METHODS = ("POST", "PATCH", "PUT")


def _next_link(suiteql_response: Dict[str, Any]) -> Optional[str]:
    """Return the absolute URL of the `next` link from a SuiteQL response, or None."""
    if not suiteql_response.get("hasMore"):
        return None
    for link in suiteql_response.get("links") or ():
        if link.get("rel") == "next":
            return link.get("href")
    return None


# Matches an `ORDER BY` clause (case-insensitive). Word boundaries prevent
# false positives on column names like `order_by_id`. The heuristic
# deliberately fires on subquery ORDER BY's too, since those can also
# surface the NetSuite empty-result quirk.
_ORDER_BY_RE = re.compile(r"\border\s+by\b", re.IGNORECASE)

# Below this threshold, `ORDER BY` is at risk of NetSuite's
# zero-row quirk (jacobsvante/netsuite#29).
_ORDER_BY_SAFE_LIMIT = 1000


class NetSuiteRestApi(rest_api_base.RestApiBase):
    def __init__(
        self,
        config: Config,
        *,
        default_timeout: int = 60,
        concurrent_requests: int = 10,
        signature_method: str = rest_api_base.DEFAULT_SIGNATURE_METHOD,
        max_retries_on_429: int = rest_api_base.DEFAULT_MAX_RETRIES_ON_429,
    ):
        self._config = config
        self._default_timeout = default_timeout
        self._concurrent_requests = concurrent_requests
        self._signature_method = signature_method
        self._max_retries_on_429 = max_retries_on_429

    @cached_property
    def hostname(self) -> str:
        return self._make_hostname()

    async def request(self, method: str, subpath: str, **request_kw):
        return await self._request_impl(method, subpath, **request_kw)

    async def get(self, subpath: str, **request_kw):
        return await self._request("GET", subpath, **request_kw)

    async def post(self, subpath: str, **request_kw):
        return await self._request(
            "POST",
            subpath,
            **request_kw,
        )

    async def put(self, subpath: str, **request_kw):
        return await self._request("PUT", subpath, **request_kw)

    async def patch(self, subpath: str, **request_kw):
        return await self._request("PATCH", subpath, **request_kw)

    async def delete(self, subpath: str, **request_kw):
        return await self._request("DELETE", subpath, **request_kw)

    # TODO maybe break out params vs poping?
    async def suiteql(self, q: str, limit: int = 10, offset: int = 0, **request_kw):
        """
        Run a single SuiteQL query.

        Example:
        >>> suiteql(q="SELECT * FROM Transaction", limit=10, offset=0)

        Note on `ORDER BY`: NetSuite has a known quirk where a SuiteQL query
        with `ORDER BY` and a small `limit` (the default 10) can return zero
        items. If you hit this, request a larger page (`limit=1000`) or sort
        client-side after fetching. This method also logs a warning when it
        detects the pattern. See jacobsvante/netsuite#29.

        Note on pagination: NetSuite caps `limit` at 1000. To stream every
        page until exhaustion, use `suiteql_paginated` instead.

        Documentation:

        - https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_156257799794.html#Using-SuiteQL
        """
        if _ORDER_BY_RE.search(q) and limit < _ORDER_BY_SAFE_LIMIT:
            logger.warning(
                "SuiteQL query contains `ORDER BY` with limit=%d. NetSuite "
                "has a known quirk where this combination can return zero "
                "rows. Consider raising limit to %d or sorting client-side. "
                "See jacobsvante/netsuite#29.",
                limit,
                _ORDER_BY_SAFE_LIMIT,
            )
        return await self._request(
            "POST",
            "/query/v1/suiteql",
            headers={"Prefer": "transient", **request_kw.pop("headers", {})},
            json={"q": q, **request_kw.pop("json", {})},
            # limit & offset look like the only available params
            params={"limit": limit, "offset": offset, **request_kw.pop("params", {})},
            **request_kw,
        )

    async def suiteql_paginated(
        self,
        q: str,
        *,
        limit: int = 1000,
        offset: int = 0,
        **request_kw,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Async generator yielding each page of a SuiteQL query, following the
        `next` link in NetSuite's response until `hasMore` is False.

        Yields the raw page dict (with `items`, `count`, `hasMore`, `links`,
        etc.). Use `limit=1000` (the NetSuite max) to minimize round trips.

        Example:
        >>> async for page in rest_api.suiteql_paginated(q="SELECT id FROM transaction"):
        ...     for row in page["items"]:
        ...         ...

        Caveat: a single SuiteQL query can return at most 100,000 rows in
        total — that is a NetSuite-side cap, not a library limitation. To
        retrieve more, partition the query with a WHERE clause (e.g. on
        `id` ranges or date windows) and run several paginated queries.
        See jacobsvante/netsuite#42.
        """
        # First page goes through the normal `suiteql` path so users get
        # consistent header/param handling. Subsequent pages follow the
        # absolute `next` link from each response.
        page = await self.suiteql(q, limit=limit, offset=offset, **request_kw)
        yield page

        next_url = _next_link(page)
        # Subsequent pages reuse the same body; only the URL (with offset)
        # changes. We forward `**request_kw` so callers' headers/params
        # still apply.
        body_kw = {
            "headers": {"Prefer": "transient", **request_kw.pop("headers", {})},
            "json": {"q": q, **request_kw.pop("json", {})},
        }
        # `params` are encoded in the next URL, so we must not also pass
        # them here — that would double-up offset/limit.
        request_kw.pop("params", None)

        while next_url is not None:
            page = await self._request(
                "POST",
                # `subpath` is ignored when `url` is provided, but
                # `_request_impl` still requires the parameter.
                "/query/v1/suiteql",
                url=next_url,
                **body_kw,
                **request_kw,
            )
            yield page
            next_url = _next_link(page)

    async def jsonschema(self, record_type: str, **request_kw):
        headers = {
            "Accept": "application/schema+json",
            **request_kw.pop("headers", {}),
        }
        return await self._request(
            "GET",
            f"/record/v1/metadata-catalog/{record_type}",
            headers=headers,
            **request_kw,
        )

    async def token_info(self, **request_kw):
        """
        Retrieves metadata about the current token. Role, company, etc.

        https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/chapter_157017286140.html#Issue-Token-and-Revoke-Token-REST-Services-for-Token-based-Authentication
        """

        # this overrides the default URL generation: this specific endpoint hits a completely different host
        request_kw["url"] = (
            f"https://{self._config.account_slugified}.restlets.api.netsuite.com/rest/tokeninfo"
        )

        return await self._request(
            method="GET",
            # useless, but required by _request
            subpath="ignored",
            **request_kw,
        )

    async def openapi(self, record_types: Sequence[str] = (), **request_kw):
        """
        Retrieves the OpenAPI specification (metadata catalog) for the Netsuite REST API. This is the best way to
        introspect the NetSuite account and return the record structure.

        https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_1545126526.html

        Args:
            record_types (Sequence[str]): Optional. List of record types to include in the OpenAPI specification.
            **request_kw: Optional keyword arguments to be passed to the underlying request.

        Returns:
            The OpenAPI specification as a JSON object.
        """

        headers = {
            "Accept": "application/swagger+json",
            **request_kw.pop("headers", {}),
        }
        params = request_kw.pop("params", {})

        if len(record_types) > 0:
            params["select"] = ",".join(record_types)

        return await self._request(
            "GET",
            "/record/v1/metadata-catalog",
            headers=headers,
            params=params,
            **request_kw,
        )

    async def attach(
        self,
        record_type: str,
        record_id: str,
        target_type: str,
        target_id: str,
        *,
        role: Optional[Dict[str, Any]] = None,
        **request_kw,
    ):
        """
        Attach one record instance to another, defining a relationship
        between them (new in NetSuite 2026.1 REST web services).

        `record_type`/`record_id` identify the record being attached *to*;
        `target_type`/`target_id` identify the record being attached. Both
        IDs may be internal IDs or external IDs in `eid:VALUE` form.

        NetSuite currently supports attaching contact and file records only.
        When attaching a contact you may pass `role` (e.g. `{"id": "-10"}`
        or `{"externalId": "family"}`); otherwise the request body is empty.

        Returns `None` (NetSuite responds with HTTP 204 No Content).

        https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_0113084334.html
        """
        json_body = request_kw.pop("json", {})
        if role is not None:
            json_body = {"role": role, **json_body}
        return await self._request(
            "POST",
            f"/record/v1/{record_type}/{record_id}/!attach/{target_type}/{target_id}",
            json=json_body,
            **request_kw,
        )

    async def detach(
        self,
        record_type: str,
        record_id: str,
        target_type: str,
        target_id: str,
        **request_kw,
    ):
        """
        Remove the relationship between two record instances (the inverse of
        `attach`). IDs may be internal IDs or `eid:VALUE` external IDs.

        Returns `None` (HTTP 204 No Content).

        https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_0113084334.html
        """
        return await self._request(
            "POST",
            f"/record/v1/{record_type}/{record_id}/!detach/{target_type}/{target_id}",
            **request_kw,
        )

    async def create_form(
        self,
        record_type: str,
        record_id: str,
        target_type: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        **request_kw,
    ):
        """
        Run the create-form (transform) operation: load a target record with
        its fields prepopulated from a related source record, without
        submitting it (new in NetSuite 2026.1 REST web services).

        For example, transform a sales order into an item fulfillment to see
        every default field and default line ID before you POST the new
        record. Pass field overrides in `body`; the operation supports the
        `expand`, `expandSubResources` and `fields` query params via
        `params`.

        Returns the prepopulated record as a dict.

        https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_1217103046.html
        """
        headers = {
            "Accept": _CREATE_FORM_MEDIA_TYPE,
            **request_kw.pop("headers", {}),
        }
        return await self._request(
            "POST",
            f"/record/v1/{record_type}/{record_id}/!transform/{target_type}",
            headers=headers,
            json=body if body is not None else {},
            **request_kw,
        )

    async def select_options(
        self,
        record_type: str,
        fields: Union[str, Sequence[str]],
        *,
        record_id: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
        **request_kw,
    ):
        """
        Retrieve the valid select options for one or more fields on a record
        (new in NetSuite 2026.1 REST web services).

        Pass a single field name or a sequence of them in `fields` (sublist
        fields use dotted names, e.g. `line.dueToFromSubsidiary`). Omit
        `record_id` to get the options on a *new* record instance (issued as
        a POST); pass `record_id` to query an *existing* instance (issued as
        a PATCH). When the options depend on other field values, supply those
        in `body` (e.g. `{"subsidiary": {"id": 1}}`).

        Returns the response dict, with a `_selectOptions` block per requested
        field (each itself paginated: `items`/`count`/`hasMore`/
        `totalResults`).

        https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_0115100241.html
        """
        if isinstance(fields, str):
            fields = [fields]
        headers = {
            "Accept": _SELECT_OPTIONS_MEDIA_TYPE,
            **request_kw.pop("headers", {}),
        }
        params = {"fields": ",".join(fields), **request_kw.pop("params", {})}
        if record_id is None:
            method, subpath = "POST", f"/record/v1/{record_type}"
        else:
            method, subpath = "PATCH", f"/record/v1/{record_type}/{record_id}"
        return await self._request(
            method,
            subpath,
            headers=headers,
            params=params,
            json=body if body is not None else {},
            **request_kw,
        )

    async def batch(
        self,
        record_type: str,
        items: Sequence[Dict[str, Any]],
        *,
        method: str = "POST",
        idempotency_key: Optional[str] = None,
        **request_kw,
    ):
        """
        Add, update, or upsert up to 100 instances of a single record type in
        one asynchronous request (new in NetSuite 2026.1 REST web services).

        `method` is POST (create), PUT (upsert), or PATCH (update). Each item
        in `items` is a record body; PATCH/PUT items must carry an `id` or
        `externalId`. Pass `idempotency_key` to set the
        `X-NetSuite-idempotency-key` header.

        NetSuite processes the batch asynchronously, so this returns a dict
        with the HTTP `status_code`, the `location` URL of the async job
        (poll it with `get()`), and any response `body`. Unlike the other
        helpers it talks to the lower-level request layer directly, because
        the async job URL is only exposed in the `Location` response header,
        which the JSON helpers discard.

        For batch reads or deletes, use `get()`/`delete()` on the collection
        endpoint with an `ids` param instead.

        https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/article_0127092747.html
        """
        method = method.upper()
        if method not in _BATCH_METHODS:
            raise ValueError(
                f"batch() method must be one of {_BATCH_METHODS}, got "
                f"{method!r}. For batch reads/deletes use get()/delete() with "
                "an `ids` param."
            )
        headers = {
            "Prefer": "respond-async",
            "Content-Type": _COLLECTION_MEDIA_TYPE,
            **request_kw.pop("headers", {}),
        }
        if idempotency_key is not None:
            headers.setdefault("X-NetSuite-idempotency-key", idempotency_key)
        resp = await self._request_impl(
            method,
            f"/record/v1/{record_type}",
            headers=headers,
            json={"items": list(items), **request_kw.pop("json", {})},
            **request_kw,
        )
        if resp.status_code < 200 or resp.status_code > 299:
            raise NetsuiteAPIRequestError(resp.status_code, resp.text)
        body = None
        if resp.text:
            try:
                body = json.loads(resp.text)
            except Exception:
                body = None
        return {
            "status_code": resp.status_code,
            "location": resp.headers.get("Location"),
            "body": body,
        }

    async def create_record(
        self,
        record_type: str,
        record_data: Dict[str, Any],
        **request_kw,
    ) -> Union[int, str, None]:
        """
        Create a record and return the internal ID NetSuite assigns to it.

        POSTs `record_data` to `/record/v1/{record_type}`. NetSuite answers a
        successful create with HTTP 204 No Content and a `Location` header
        pointing at the new record; this parses the trailing ID segment and
        returns it as an `int` when numeric, or the raw string for external
        IDs (`eid:...`). Returns `None` if NetSuite omits the `Location`
        header.

        Talks to the lower-level request layer directly (like `batch`)
        because the new record's ID is only exposed in the `Location`
        response header, which the JSON helper `_request` discards.

        https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_1545141395.html
        """
        resp = await self._request_impl(
            "POST",
            f"/record/v1/{record_type}",
            json=record_data,
            **request_kw,
        )
        if resp.status_code < 200 or resp.status_code > 299:
            raise NetsuiteAPIRequestError(resp.status_code, resp.text)
        return self._parse_id_from_location(resp.headers.get("Location"))

    @staticmethod
    def _parse_id_from_location(location: Optional[str]) -> Union[int, str, None]:
        """Extract the record ID (last path segment) from a `Location` URL,
        ignoring any query string or fragment and tolerating a trailing
        slash. Returns an `int` for numeric IDs, the raw string otherwise,
        or `None` when no usable segment is present."""
        if not location:
            return None
        path = location.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        record_id = path.rsplit("/", 1)[-1]
        if not record_id:
            return None
        try:
            return int(record_id)
        except ValueError:
            return record_id

    def _make_hostname(self):
        return f"{self._config.account_slugified}.suitetalk.api.netsuite.com"

    def _make_url(self, subpath: str):
        return f"https://{self.hostname}/services/rest{subpath}"

    def _make_default_headers(self):
        return {
            "Content-Type": "application/json",
            "X-NetSuite-PropertyNameValidation": "error",
        }
