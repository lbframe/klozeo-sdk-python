"""Synchronous Klozeo API client."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import httpx

from ._errors import RateLimitedError
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

DEFAULT_BASE_URL = "https://api.klozeo.com/api/v1"
_RETRY_STATUSES = {429, 500, 502, 503, 504}


class Klozeo:
    """Synchronous client for the Klozeo Lead Management API.

    All methods map one-to-one to REST endpoints. The client handles
    authentication, retries, and rate-limit state tracking automatically.

    Args:
        api_key: Your Klozeo API key (``sk_live_...``).
        base_url: Override the API base URL.
        timeout: Per-request timeout in seconds.
        max_retries: Number of retries on 429 or 5xx responses.

    Example::

        from klozeo import Klozeo, Lead

        client = Klozeo("sk_live_your_api_key")
        resp = client.create(Lead(name="Acme", source="website"))
        print(resp.id)
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
        self._http = httpx.Client(
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )
        self._rate_limit_state: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "Klozeo":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Execute an HTTP request with retry logic.

        Retries on 429 (honouring ``Retry-After``) and 5xx status codes with
        exponential backoff up to ``max_retries``.
        """
        url = self._url(path)
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._http.request(method, url, **kwargs)
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise

            # Track rate-limit headers
            self._update_rate_limit_state(response)

            if response.status_code not in _RETRY_STATUSES:
                raise_for_status(response)
                return response

            if attempt >= self._max_retries:
                raise_for_status(response)

            # Determine backoff
            if response.status_code == 429:
                try:
                    wait = float(response.headers.get("Retry-After", 2 ** attempt))
                except (ValueError, TypeError):
                    wait = float(2 ** attempt)
            else:
                wait = float(2 ** attempt)

            time.sleep(wait)

        # Should not reach here, but satisfy type checkers
        if last_exc:
            raise last_exc
        raise KlozeoError("Max retries exceeded")  # type: ignore[name-defined]  # noqa: F821

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

    def create(self, lead: Lead) -> CreateResponse:
        """Create a new lead (or merge into an existing duplicate).

        Args:
            lead: The lead data. ``name`` and ``source`` are required.

        Returns:
            A :class:`CreateResponse` with the lead ``id`` and duplicate info.

        Raises:
            ForbiddenError: If the account leads limit is reached.
            BadRequestError: If required fields are missing.
        """
        response = self._request("POST", "/leads", json=lead_payload(lead))
        return CreateResponse.model_validate(response.json())

    def get(self, lead_id: str) -> Lead:
        """Fetch a single lead by ID.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).

        Returns:
            The full :class:`Lead` object.

        Raises:
            NotFoundError: If the lead does not exist.
        """
        response = self._request("GET", f"/leads/{lead_id}")
        return Lead.model_validate(response.json())

    def update(self, lead_id: str, data: UpdateLeadInput) -> Lead:
        """Partially update a lead.

        Only fields set on ``data`` are sent. All others are left unchanged
        (last-touch-wins).

        Args:
            lead_id: The lead ID (``cl_<uuid>``).
            data: Partial update payload.

        Returns:
            The updated :class:`Lead`.

        Raises:
            NotFoundError: If the lead does not exist.
        """
        response = self._request("PUT", f"/leads/{lead_id}", json=update_payload(data))
        return Lead.model_validate(response.json())

    def delete(self, lead_id: str) -> None:
        """Delete a lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).

        Raises:
            NotFoundError: If the lead does not exist.
        """
        self._request("DELETE", f"/leads/{lead_id}")

    # ------------------------------------------------------------------
    # Leads — List / Iterate
    # ------------------------------------------------------------------

    def list(
        self,
        *filters: Filter,
        sort_by: SortField | str | None = None,
        sort_order: SortOrder | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        options: ListOptions | None = None,
    ) -> ListResult:
        """List leads with optional filters, sorting and pagination.

        Positional ``filters`` and keyword arguments are merged. If ``options``
        is provided it takes precedence over all other arguments.

        Args:
            *filters: Filter objects (e.g. ``city().eq("Berlin")``).
            sort_by: Field to sort by.
            sort_order: Sort direction.
            limit: Page size (default 50, max 1000).
            cursor: Cursor from a previous :class:`ListResult`.
            options: A :class:`ListOptions` builder — takes precedence when set.

        Returns:
            A :class:`ListResult` with ``leads``, ``next_cursor``, ``has_more``,
            and ``count``.
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
        response = self._request("GET", "/leads", params=params)
        return ListResult.model_validate(response.json())

    def iterate(
        self,
        *filters: Filter,
        sort_by: SortField | str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Iterator[Lead]:
        """Iterate over all leads matching the given filters, fetching pages automatically.

        Args:
            *filters: Filter objects.
            sort_by: Field to sort by.
            sort_order: Sort direction.

        Yields:
            :class:`Lead` objects, one at a time across all pages.

        Example::

            for lead in client.iterate(city().eq("Berlin")):
                print(lead.name)
        """
        cursor: str | None = None
        while True:
            result = self.list(*filters, sort_by=sort_by, sort_order=sort_order, cursor=cursor)
            yield from result.leads
            if not result.has_more or not result.next_cursor:
                break
            cursor = result.next_cursor

    # ------------------------------------------------------------------
    # Leads — Batch
    # ------------------------------------------------------------------

    def batch_create(self, leads: list[Lead]) -> BatchCreateResult:
        """Create up to 100 leads in a single request.

        Args:
            leads: List of leads to create. Maximum 100 (free) or 500 (pro).

        Returns:
            A :class:`BatchCreateResult` with ``created``, ``errors``, and counts.
        """
        payload = {"leads": [lead_payload(lead) for lead in leads]}
        response = self._request("POST", "/leads/batch", json=payload)
        return BatchCreateResult.model_validate(response.json())

    def batch_update(self, ids: list[str], data: UpdateLeadInput) -> BatchResult:
        """Apply the same partial update to multiple leads at once.

        Args:
            ids: List of lead IDs to update.
            data: Partial update to apply to all leads.

        Returns:
            A :class:`BatchResult` with per-item outcomes.
        """
        payload = {"ids": ids, "data": update_payload(data)}
        response = self._request("PUT", "/leads/batch", json=payload)
        return BatchResult.model_validate(response.json())

    def batch_delete(self, ids: list[str]) -> BatchResult:
        """Delete multiple leads in a single request.

        Args:
            ids: List of lead IDs to delete.

        Returns:
            A :class:`BatchResult` with per-item outcomes.
        """
        response = self._request("DELETE", "/leads/batch", json={"ids": ids})
        return BatchResult.model_validate(response.json())

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(
        self,
        format: ExportFormat,
        *filters: Filter,
        sort_by: SortField | str | None = None,
        sort_order: SortOrder | None = None,
    ) -> bytes:
        """Export all leads matching the given filters.

        No pagination — returns the complete result set as raw bytes.

        Args:
            format: Output format (``ExportFormat.CSV``, ``.JSON``, ``.XLSX``).
            *filters: Filter objects to narrow the export.
            sort_by: Field to sort by.
            sort_order: Sort direction.

        Returns:
            Raw bytes of the export file.

        Example::

            data = client.export(ExportFormat.CSV)
            with open("leads.csv", "wb") as f:
                f.write(data)
        """
        params = build_export_params(
            format.value if isinstance(format, ExportFormat) else format,
            filters,
            sort_by,
            sort_order,
        )
        response = self._request("GET", "/leads/export", params=params)
        return response.content

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def create_note(self, lead_id: str, content: str) -> Note:
        """Create a note on a lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).
            content: Note text.

        Returns:
            The created :class:`Note`.
        """
        response = self._request("POST", f"/leads/{lead_id}/notes", json={"content": content})
        return Note.model_validate(response.json())

    def list_notes(self, lead_id: str) -> list[Note]:
        """List all notes for a lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).

        Returns:
            List of :class:`Note` objects.
        """
        response = self._request("GET", f"/leads/{lead_id}/notes")
        data = response.json()
        return [Note.model_validate(n) for n in data.get("notes", [])]

    def update_note(self, note_id: str, content: str) -> Note:
        """Update the content of an existing note.

        Args:
            note_id: The note ID (``note_<uuid>``).
            content: New note text.

        Returns:
            The updated :class:`Note`.
        """
        response = self._request("PUT", f"/notes/{note_id}", json={"content": content})
        return Note.model_validate(response.json())

    def delete_note(self, note_id: str) -> None:
        """Delete a note.

        Args:
            note_id: The note ID (``note_<uuid>``).
        """
        self._request("DELETE", f"/notes/{note_id}")

    # ------------------------------------------------------------------
    # Dynamic Attributes
    # ------------------------------------------------------------------

    def list_attributes(self, lead_id: str) -> list[Attribute]:
        """List all custom attributes for a lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).

        Returns:
            List of :class:`Attribute` objects.
        """
        response = self._request("GET", f"/leads/{lead_id}/attributes")
        data = response.json()
        return [Attribute.model_validate(a) for a in data.get("attributes", [])]

    def create_attribute(self, lead_id: str, attribute: Attribute) -> Attribute:
        """Create a custom attribute on a lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).
            attribute: The attribute to create.

        Returns:
            The created :class:`Attribute` with its server-assigned ``id``.
        """
        response = self._request(
            "POST",
            f"/leads/{lead_id}/attributes",
            json=attribute.model_dump(exclude_none=True),
        )
        return Attribute.model_validate(response.json())

    def update_attribute(self, lead_id: str, attr_id: str, value: Any) -> None:
        """Update the value of a custom attribute.

        The API expects the raw JSON value only (no wrapper object).

        Args:
            lead_id: The lead ID (``cl_<uuid>``).
            attr_id: The attribute UUID.
            value: New value (string, number, bool, list, or dict).
        """
        import json as _json

        self._request(
            "PUT",
            f"/leads/{lead_id}/attributes/{attr_id}",
            content=_json.dumps(value),
            headers={"Content-Type": "application/json"},
        )

    def delete_attribute(self, lead_id: str, attr_id: str) -> None:
        """Delete a custom attribute from a lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).
            attr_id: The attribute UUID.
        """
        self._request("DELETE", f"/leads/{lead_id}/attributes/{attr_id}")

    # ------------------------------------------------------------------
    # Scoring Rules
    # ------------------------------------------------------------------

    def list_scoring_rules(self) -> list[ScoringRule]:
        """List all scoring rules for the account.

        Returns:
            List of :class:`ScoringRule` objects.
        """
        response = self._request("GET", "/scoring-rules")
        data = response.json()
        return [ScoringRule.model_validate(r) for r in data.get("rules", [])]

    def create_scoring_rule(self, rule: ScoringRuleInput) -> ScoringRule:
        """Create a new scoring rule.

        Args:
            rule: The scoring rule to create.

        Returns:
            The created :class:`ScoringRule` with its server-assigned ``id``.
        """
        response = self._request("POST", "/scoring-rules", json=rule.model_dump(exclude_none=True))
        return ScoringRule.model_validate(response.json())

    def get_scoring_rule(self, rule_id: str) -> ScoringRule:
        """Fetch a scoring rule by ID.

        Args:
            rule_id: The scoring rule UUID.

        Returns:
            The :class:`ScoringRule`.

        Raises:
            NotFoundError: If the rule does not exist.
        """
        response = self._request("GET", f"/scoring-rules/{rule_id}")
        return ScoringRule.model_validate(response.json())

    def update_scoring_rule(self, rule_id: str, data: ScoringRuleInput) -> None:
        """Update a scoring rule.

        Args:
            rule_id: The scoring rule UUID.
            data: Partial update payload.
        """
        self._request("PUT", f"/scoring-rules/{rule_id}", json=data.model_dump(exclude_none=True))

    def delete_scoring_rule(self, rule_id: str) -> None:
        """Delete a scoring rule.

        Args:
            rule_id: The scoring rule UUID.
        """
        self._request("DELETE", f"/scoring-rules/{rule_id}")

    def recalculate_score(self, lead_id: str) -> float:
        """Recalculate and persist the score for a single lead.

        Args:
            lead_id: The lead ID (``cl_<uuid>``).

        Returns:
            The new score as a float.
        """
        response = self._request("POST", f"/leads/{lead_id}/score")
        data = response.json()
        return float(data.get("score", 0))

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    def list_webhooks(self) -> list[Webhook]:
        """List all webhooks for the account.

        Returns:
            List of :class:`Webhook` objects.
        """
        response = self._request("GET", "/webhooks")
        data = response.json()
        return [Webhook.model_validate(w) for w in data.get("webhooks", [])]

    def create_webhook(self, webhook: WebhookInput) -> Webhook:
        """Create a new webhook subscription.

        Args:
            webhook: The webhook configuration.

        Returns:
            The created :class:`Webhook` with its server-assigned ``id``.
        """
        response = self._request("POST", "/webhooks", json=webhook.model_dump(exclude_none=True))
        return Webhook.model_validate(response.json())

    def delete_webhook(self, webhook_id: str) -> None:
        """Delete a webhook subscription.

        Args:
            webhook_id: The webhook UUID.
        """
        self._request("DELETE", f"/webhooks/{webhook_id}")
