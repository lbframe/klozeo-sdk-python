"""Internal helpers for the Klozeo SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from ._errors import (
    BadRequestError,
    ForbiddenError,
    KlozeoError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
)
from ._filters import Filter
from ._models import SortField, SortOrder

if TYPE_CHECKING:
    pass


def build_list_params(
    filters: tuple[Any, ...],
    sort_by: "SortField | str | None",
    sort_order: "SortOrder | None",
    limit: int | None,
    cursor: str | None,
) -> list[tuple[str, str]]:
    """Serialize list/iterate parameters into ``(key, value)`` pairs.

    Repeated ``filter=`` params are represented as multiple tuples with the
    same key, which is how ``httpx`` handles repeated query parameters.

    Args:
        filters: Sequence of :class:`~._filters.Filter` objects.
        sort_by: Sort field enum value or raw string.
        sort_order: ``SortOrder.ASC`` or ``SortOrder.DESC``.
        limit: Page size.
        cursor: Pagination cursor.

    Returns:
        A list of ``(key, value)`` pairs suitable for ``params=`` in httpx.
    """
    params: list[tuple[str, str]] = []

    for f in filters:
        if isinstance(f, Filter):
            params.append(("filter", f.to_param()))

    if sort_by is not None:
        params.append(("sort_by", sort_by.value if isinstance(sort_by, SortField) else str(sort_by)))

    if sort_order is not None:
        params.append(("sort_order", sort_order.value if isinstance(sort_order, SortOrder) else str(sort_order)))

    if limit is not None:
        params.append(("limit", str(limit)))

    if cursor is not None:
        params.append(("cursor", cursor))

    return params


def build_export_params(
    format: str,
    filters: tuple[Any, ...],
    sort_by: "SortField | str | None",
    sort_order: "SortOrder | None",
) -> list[tuple[str, str]]:
    """Serialize export parameters.

    Args:
        format: Export format string (``"csv"``, ``"json"``, ``"xlsx"``).
        filters: Sequence of :class:`~._filters.Filter` objects.
        sort_by: Sort field.
        sort_order: Sort direction.

    Returns:
        A list of ``(key, value)`` pairs.
    """
    params: list[tuple[str, str]] = [("format", format)]
    for f in filters:
        if isinstance(f, Filter):
            params.append(("filter", f.to_param()))
    if sort_by is not None:
        params.append(("sort_by", sort_by.value if isinstance(sort_by, SortField) else str(sort_by)))
    if sort_order is not None:
        params.append(("sort_order", sort_order.value if isinstance(sort_order, SortOrder) else str(sort_order)))
    return params


def raise_for_status(response: httpx.Response) -> None:
    """Parse an error response body and raise a typed exception.

    Args:
        response: The ``httpx.Response`` object.

    Raises:
        UnauthorizedError: On HTTP 401.
        ForbiddenError: On HTTP 403.
        NotFoundError: On HTTP 404.
        RateLimitedError: On HTTP 429.
        BadRequestError: On HTTP 400.
        KlozeoError: On any other 4xx/5xx status.
    """
    if response.is_success:
        return

    message = ""
    code = ""
    try:
        body = response.json()
        message = body.get("message") or body.get("error") or ""
        code = body.get("code") or ""
    except Exception:
        message = response.text or f"HTTP {response.status_code}"

    status = response.status_code

    match status:
        case 400:
            raise BadRequestError(message or "Bad request", code or "bad_request")
        case 401:
            raise UnauthorizedError(message or "Unauthorized", code or "unauthorized")
        case 403:
            raise ForbiddenError(message or "Forbidden", code or "forbidden")
        case 404:
            raise NotFoundError(message or "Not found", code or "not_found")
        case 429:
            retry_after = 0.0
            try:
                retry_after = float(response.headers.get("Retry-After", "0"))
            except (ValueError, TypeError):
                pass
            raise RateLimitedError(message or "Rate limit exceeded", code or "rate_limit_exceeded", retry_after)
        case _:
            raise KlozeoError(message or f"HTTP {status}", status_code=status, code=code or "internal_error")


def lead_payload(lead: Any) -> dict[str, Any]:
    """Serialise a :class:`~._models.Lead` to a JSON-safe dict, omitting ``None`` values
    and read-only server fields.

    Args:
        lead: A :class:`~._models.Lead` instance.

    Returns:
        A dict suitable for use as a JSON request body.
    """
    exclude = {"id", "score", "created_at", "updated_at", "last_interaction_at"}
    data = lead.model_dump(exclude_none=True)
    for key in exclude:
        data.pop(key, None)

    # Serialise Attribute objects inside the list
    if "attributes" in data:
        data["attributes"] = [
            a.model_dump(exclude_none=True) if hasattr(a, "model_dump") else a
            for a in data["attributes"]
        ]

    return data


def update_payload(update: Any) -> dict[str, Any]:
    """Serialise an :class:`~._models.UpdateLeadInput` omitting ``None`` values.

    Args:
        update: An :class:`~._models.UpdateLeadInput` instance.

    Returns:
        A dict suitable for use as a JSON request body.
    """
    return update.model_dump(exclude_none=True)
