"""Asynchronous Klozeo API client."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ._filters import Filter
from ._models import (
    Attribute,
    BatchCreateResult,
    BatchResult,
    CreateResponse,
    ExportFormat,
    Lead,
    ListOptions,
    ListResult,
    Note,
    ScoringRule,
    ScoringRuleInput,
    SortField,
    SortOrder,
    UpdateLeadInput,
    Webhook,
    WebhookInput,
)
from ._utils import (
    build_export_params,
    build_list_params,
    lead_payload,
    raise_for_status,
    update_payload,
)
from ._client import DEFAULT_BASE_URL, _RETRY_STATUSES

_TRANSPORT_ERRORS = (httpx.TransportError,)


class AsyncKlozeo:
    """Asynchronous client for the Klozeo Lead Management API.

    Mirrors the :class:`~._client.Klozeo` sync client with ``async``/``await``.

    Args:
        api_key: Your Klozeo API key (``sk_live_...``).
        base_url: Override the API base URL.
        timeout: Per-request timeout in seconds.
        max_retries: Number of retries on 429 or 5xx responses.

    Example::

        import asyncio
        from klozeo import AsyncKlozeo, Lead

        async def main():
            async with AsyncKlozeo("sk_live_your_api_key") as client:
                resp = await client.create(Lead(name="Acme", source="website"))
                print(resp.id)

        asyncio.run(main())
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._http = httpx.AsyncClient(
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )
        self._rate_limit_state: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "AsyncKlozeo":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying async HTTP connection pool."""
        await self._http.aclose()

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{path.lstrip('/')}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Execute an async HTTP request with retry logic."""
        url = self._url(path)
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._http.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

            self._update_rate_limit_state(response)

            if response.status_code not in _RETRY_STATUSES:
                raise_for_status(response)
                return response

            if attempt >= self._max_retries:
                raise_for_status(response)

            if response.status_code == 429:
                try:
                    wait = float(response.headers.get("Retry-After", 2 ** attempt))
                except (ValueError, TypeError):
                    wait = float(2 ** attempt)
            else:
                wait = float(2 ** attempt)

            await asyncio.sleep(wait)

        if last_exc:
            raise last_exc
        from ._errors import KlozeoError
        raise KlozeoError("Max retries exceeded")

    def _update_rate_limit_state(self, response: httpx.Response) -> None:
        for header in ("X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"):
            value = response.headers.get(header)
            if value is not None:
                self._rate_limit_state[header] = value

    def rate_limit_state(self) -> dict[str, str]:
        """Return the last-seen rate-limit headers as a dict.

        Returns:
            A dict with keys ``X-RateLimit-Limit``, ``X-RateLimit-Remaining``,
            and optionally ``Retry-After``.
        """
        return dict(self._rate_limit_state)

    # ------------------------------------------------------------------
    # Leads — CRUD
    # ------------------------------------------------------------------

    async def create(self, lead: Lead) -> CreateResponse:
        """Create a new lead (or merge into an existing duplicate).

        Args:
            lead: The lead data. ``name`` and ``source`` are required.

        Returns:
            A :class:`CreateResponse` with the lead ``id`` and duplicate info.

        Raises:
            ForbiddenError: If the account leads limit is reached.
        """
        response = await self._request("POST", "/leads", json=lead_payload(lead))
        return CreateResponse.model_validate(response.json())

    async def get(self, lead_id: str) -> Lead:
        """Fetch a single lead by ID.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).

        Returns:
            The full :class:`Lead` object.

        Raises:
            NotFoundError: If the lead does not exist.
        """
        response = await self._request("GET", f"/leads/{lead_id}")
        return Lead.model_validate(response.json())

    async def update(self, lead_id: str, data: UpdateLeadInput) -> Lead:
        """Partially update a lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).
            data: Partial update payload.

        Returns:
            The updated :class:`Lead`.

        Raises:
            NotFoundError: If the lead does not exist.
        """
        response = await self._request("PUT", f"/leads/{lead_id}", json=update_payload(data))
        return Lead.model_validate(response.json())

    async def delete(self, lead_id: str) -> None:
        """Delete a lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).
        """
        await self._request("DELETE", f"/leads/{lead_id}")

    # ------------------------------------------------------------------
    # Leads — List / Iterate
    # ------------------------------------------------------------------

    async def list(
        self,
        *filters: Filter,
        sort_by: SortField | str | None = None,
        sort_order: SortOrder | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        options: ListOptions | None = None,
    ) -> ListResult:
        """List leads with optional filters, sorting and pagination.

        Args:
            *filters: Filter objects.
            sort_by: Field to sort by.
            sort_order: Sort direction.
            limit: Page size (default 50, max 1000).
            cursor: Cursor from a previous :class:`ListResult`.
            options: :class:`ListOptions` builder — takes precedence when set.

        Returns:
            A :class:`ListResult`.
        """
        if options is not None:
            resolved_filters = tuple(options._filters)
            resolved_sort_by = options._sort_by
            resolved_sort_order = options._sort_order
            resolved_limit = options._limit
            resolved_cursor = options._cursor
        else:
            resolved_filters = filters
            resolved_sort_by = sort_by
            resolved_sort_order = sort_order
            resolved_limit = limit
            resolved_cursor = cursor

        params = build_list_params(
            resolved_filters, resolved_sort_by, resolved_sort_order, resolved_limit, resolved_cursor
        )
        response = await self._request("GET", "/leads", params=params)
        return ListResult.model_validate(response.json())

    async def iterate(
        self,
        *filters: Filter,
        sort_by: SortField | str | None = None,
        sort_order: SortOrder | None = None,
    ) -> AsyncIterator[Lead]:
        """Async-iterate over all leads, fetching pages transparently.

        Args:
            *filters: Filter objects.
            sort_by: Field to sort by.
            sort_order: Sort direction.

        Yields:
            :class:`Lead` objects across all pages.

        Example::

            async for lead in client.iterate(city().eq("Berlin")):
                print(lead.name)
        """
        cursor: str | None = None
        while True:
            result = await self.list(*filters, sort_by=sort_by, sort_order=sort_order, cursor=cursor)
            for lead in result.leads:
                yield lead
            if not result.has_more or not result.next_cursor:
                break
            cursor = result.next_cursor

    # ------------------------------------------------------------------
    # Leads — Batch
    # ------------------------------------------------------------------

    async def batch_create(self, leads: list[Lead]) -> BatchCreateResult:
        """Create up to 100 leads in a single request.

        Args:
            leads: List of leads to create.

        Returns:
            A :class:`BatchCreateResult`.
        """
        payload = {"leads": [lead_payload(lead) for lead in leads]}
        response = await self._request("POST", "/leads/batch", json=payload)
        return BatchCreateResult.model_validate(response.json())

    async def batch_update(self, ids: list[str], data: UpdateLeadInput) -> BatchResult:
        """Apply the same partial update to multiple leads at once.

        Args:
            ids: List of lead IDs.
            data: Partial update to apply.

        Returns:
            A :class:`BatchResult`.
        """
        payload = {"ids": ids, "data": update_payload(data)}
        response = await self._request("PUT", "/leads/batch", json=payload)
        return BatchResult.model_validate(response.json())

    async def batch_delete(self, ids: list[str]) -> BatchResult:
        """Delete multiple leads in a single request.

        Args:
            ids: List of lead IDs to delete.

        Returns:
            A :class:`BatchResult`.
        """
        response = await self._request("DELETE", "/leads/batch", json={"ids": ids})
        return BatchResult.model_validate(response.json())

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def export(
        self,
        format: ExportFormat,
        *filters: Filter,
        sort_by: SortField | str | None = None,
        sort_order: SortOrder | None = None,
    ) -> bytes:
        """Export all matching leads as raw bytes.

        Args:
            format: Output format.
            *filters: Filter objects.
            sort_by: Sort field.
            sort_order: Sort direction.

        Returns:
            Raw bytes of the export file.
        """
        params = build_export_params(
            format.value if isinstance(format, ExportFormat) else format,
            filters,
            sort_by,
            sort_order,
        )
        response = await self._request("GET", "/leads/export", params=params)
        return response.content

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    async def create_note(self, lead_id: str, content: str) -> Note:
        """Create a note on a lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).
            content: Note text.

        Returns:
            The created :class:`Note`.
        """
        response = await self._request("POST", f"/leads/{lead_id}/notes", json={"content": content})
        return Note.model_validate(response.json())

    async def list_notes(self, lead_id: str) -> list[Note]:
        """List all notes for a lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).

        Returns:
            List of :class:`Note` objects.
        """
        response = await self._request("GET", f"/leads/{lead_id}/notes")
        data = response.json()
        return [Note.model_validate(n) for n in data.get("notes", [])]

    async def update_note(self, note_id: str, content: str) -> Note:
        """Update note content.

        Args:
            note_id: The note ID (``note_<uuid>``).
            content: New note text.

        Returns:
            The updated :class:`Note`.
        """
        response = await self._request("PUT", f"/notes/{note_id}", json={"content": content})
        return Note.model_validate(response.json())

    async def delete_note(self, note_id: str) -> None:
        """Delete a note.

        Args:
            note_id: The note ID (``note_<uuid>``).
        """
        await self._request("DELETE", f"/notes/{note_id}")

    # ------------------------------------------------------------------
    # Dynamic Attributes
    # ------------------------------------------------------------------

    async def list_attributes(self, lead_id: str) -> list[Attribute]:
        """List all custom attributes for a lead.

        Args:
            lead_id: The lead ID.

        Returns:
            List of :class:`Attribute` objects.
        """
        response = await self._request("GET", f"/leads/{lead_id}/attributes")
        data = response.json()
        return [Attribute.model_validate(a) for a in data.get("attributes", [])]

    async def create_attribute(self, lead_id: str, attribute: Attribute) -> Attribute:
        """Create a custom attribute on a lead.

        Args:
            lead_id: The lead ID.
            attribute: The attribute to create.

        Returns:
            The created :class:`Attribute` with its server-assigned ``id``.
        """
        response = await self._request(
            "POST",
            f"/leads/{lead_id}/attributes",
            json=attribute.model_dump(exclude_none=True),
        )
        return Attribute.model_validate(response.json())

    async def update_attribute(self, lead_id: str, attr_id: str, value: Any) -> None:
        """Update the value of a custom attribute.

        Args:
            lead_id: The lead ID.
            attr_id: The attribute UUID.
            value: New value (string, number, bool, list, or dict).
        """
        import json as _json

        await self._request(
            "PUT",
            f"/leads/{lead_id}/attributes/{attr_id}",
            content=_json.dumps(value),
            headers={"Content-Type": "application/json"},
        )

    async def delete_attribute(self, lead_id: str, attr_id: str) -> None:
        """Delete a custom attribute from a lead.

        Args:
            lead_id: The lead ID.
            attr_id: The attribute UUID.
        """
        await self._request("DELETE", f"/leads/{lead_id}/attributes/{attr_id}")

    # ------------------------------------------------------------------
    # Scoring Rules
    # ------------------------------------------------------------------

    async def list_scoring_rules(self) -> list[ScoringRule]:
        """List all scoring rules for the account.

        Returns:
            List of :class:`ScoringRule` objects.
        """
        response = await self._request("GET", "/scoring-rules")
        data = response.json()
        return [ScoringRule.model_validate(r) for r in data.get("rules", [])]

    async def create_scoring_rule(self, rule: ScoringRuleInput) -> ScoringRule:
        """Create a new scoring rule.

        Args:
            rule: The scoring rule to create.

        Returns:
            The created :class:`ScoringRule`.
        """
        response = await self._request("POST", "/scoring-rules", json=rule.model_dump(exclude_none=True))
        return ScoringRule.model_validate(response.json())

    async def get_scoring_rule(self, rule_id: str) -> ScoringRule:
        """Fetch a scoring rule by ID.

        Args:
            rule_id: The scoring rule UUID.

        Returns:
            The :class:`ScoringRule`.
        """
        response = await self._request("GET", f"/scoring-rules/{rule_id}")
        return ScoringRule.model_validate(response.json())

    async def update_scoring_rule(self, rule_id: str, data: ScoringRuleInput) -> None:
        """Update a scoring rule.

        Args:
            rule_id: The scoring rule UUID.
            data: Partial update payload.
        """
        await self._request("PUT", f"/scoring-rules/{rule_id}", json=data.model_dump(exclude_none=True))

    async def delete_scoring_rule(self, rule_id: str) -> None:
        """Delete a scoring rule.

        Args:
            rule_id: The scoring rule UUID.
        """
        await self._request("DELETE", f"/scoring-rules/{rule_id}")

    async def recalculate_score(self, lead_id: str) -> float:
        """Recalculate and persist the score for a single lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).

        Returns:
            The new score as a float.
        """
        response = await self._request("POST", f"/leads/{lead_id}/score")
        data = response.json()
        return float(data.get("score", 0))

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    async def list_webhooks(self) -> list[Webhook]:
        """List all webhooks for the account.

        Returns:
            List of :class:`Webhook` objects.
        """
        response = await self._request("GET", "/webhooks")
        data = response.json()
        return [Webhook.model_validate(w) for w in data.get("webhooks", [])]

    async def create_webhook(self, webhook: WebhookInput) -> Webhook:
        """Create a new webhook subscription.

        Args:
            webhook: The webhook configuration.

        Returns:
            The created :class:`Webhook`.
        """
        response = await self._request("POST", "/webhooks", json=webhook.model_dump(exclude_none=True))
        return Webhook.model_validate(response.json())

    async def delete_webhook(self, webhook_id: str) -> None:
        """Delete a webhook subscription.

        Args:
            webhook_id: The webhook UUID.
        """
        await self._request("DELETE", f"/webhooks/{webhook_id}")
