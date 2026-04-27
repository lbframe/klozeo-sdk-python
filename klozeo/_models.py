"""Pydantic models for the Klozeo SDK."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SortField(str, Enum):
    """Fields that can be used to sort lead results."""

    NAME = "name"
    CITY = "city"
    COUNTRY = "country"
    STATE = "state"
    CATEGORY = "category"
    SOURCE = "source"
    EMAIL = "email"
    PHONE = "phone"
    WEBSITE = "website"
    RATING = "rating"
    REVIEW_COUNT = "review_count"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    LAST_INTERACTION_AT = "last_interaction_at"


class SortOrder(str, Enum):
    """Sort direction."""

    ASC = "ASC"
    DESC = "DESC"


class ExportFormat(str, Enum):
    """Supported export file formats."""

    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"


# ---------------------------------------------------------------------------
# Attribute
# ---------------------------------------------------------------------------


class Attribute(BaseModel):
    """A dynamic custom attribute attached to a lead.

    Attributes:
        name: Attribute name (e.g. ``"industry"``).
        type: One of ``"text"``, ``"number"``, ``"bool"``, ``"list"``, ``"object"``.
        value: The attribute value — type depends on the ``type`` field.
        id: Server-assigned UUID (only present on attributes returned from the API).
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str
    type: str
    value: Any
    id: str | None = None


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------


class Lead(BaseModel):
    """A lead record.

    Required fields when creating: ``name`` and ``source``.
    All other fields are optional. Read-only fields (``id``, ``score``,
    ``created_at``, ``updated_at``, ``last_interaction_at``) are set by the
    server and returned in API responses.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Required
    name: str
    source: str

    # Optional write fields
    description: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    rating: float | None = None
    review_count: int | None = None
    category: str | None = None
    tags: list[str] | None = None
    source_id: str | None = None
    logo_url: str | None = None
    status: str | None = None
    attributes: list[Attribute] | None = None

    # Read-only (server-set)
    id: str | None = None
    score: float | None = None
    created_at: int | None = None
    updated_at: int | None = None
    last_interaction_at: int | None = None


class UpdateLeadInput(BaseModel):
    """Partial update payload for a lead.

    All fields are optional — only the fields you provide are sent to the API,
    following a last-touch-wins merge strategy.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    source: str | None = None
    description: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    rating: float | None = None
    review_count: int | None = None
    category: str | None = None
    tags: list[str] | None = None
    source_id: str | None = None
    logo_url: str | None = None
    status: str | None = None


# ---------------------------------------------------------------------------
# Note
# ---------------------------------------------------------------------------


class Note(BaseModel):
    """A note attached to a lead.

    Attributes:
        id: Server-assigned note ID (``note_<uuid>``).
        lead_id: The lead this note belongs to.
        content: The note text.
        created_at: Unix timestamp of creation.
        updated_at: Unix timestamp of last update.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    lead_id: str | None = None
    content: str
    created_at: int | None = None
    updated_at: int | None = None


# ---------------------------------------------------------------------------
# Scoring Rule
# ---------------------------------------------------------------------------


class ScoringRule(BaseModel):
    """A scoring rule used to calculate lead scores.

    Attributes:
        id: Server-assigned UUID.
        name: Human-readable rule name.
        expression: Expression string evaluated against each lead.
        priority: Evaluation order — lower value = higher priority.
        created_at: Unix timestamp of creation.
        updated_at: Unix timestamp of last update.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    name: str
    expression: str
    priority: int = 0
    created_at: int | None = None
    updated_at: int | None = None


class ScoringRuleInput(BaseModel):
    """Input payload for creating or updating a scoring rule."""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    expression: str | None = None
    priority: int | None = None


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------


class Webhook(BaseModel):
    """A webhook subscription.

    Attributes:
        id: Server-assigned UUID.
        url: Destination URL for POST notifications.
        events: List of event names subscribed to.
        active: Whether the webhook is currently active.
        created_at: ISO 8601 creation timestamp (string as returned by the API).
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    url: str
    events: list[str] | None = None
    active: bool | None = None
    created_at: str | None = None


class WebhookInput(BaseModel):
    """Input payload for creating a webhook."""

    model_config = ConfigDict(populate_by_name=True)

    url: str
    events: list[str] | None = None
    secret: str | None = None


# ---------------------------------------------------------------------------
# Response wrappers
# ---------------------------------------------------------------------------


class CreateResponse(BaseModel):
    """Response from a lead create operation.

    Attributes:
        id: The lead ID (``cl_<uuid>``).
        message: Human-readable result description.
        created_at: Unix timestamp of creation.
        duplicate: ``True`` if an existing lead was merged.
        potential_duplicate_id: ID of a suspected low-confidence duplicate.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    message: str | None = None
    created_at: int | None = None
    duplicate: bool | None = None
    potential_duplicate_id: str | None = None


class ListResult(BaseModel):
    """Paginated list of leads.

    Attributes:
        leads: The leads on this page.
        next_cursor: Opaque cursor token — pass to the next ``list()`` call.
        has_more: Whether more pages are available.
        count: Number of leads in this page.
    """

    model_config = ConfigDict(populate_by_name=True)

    leads: list[Lead]
    next_cursor: str | None = None
    has_more: bool = False
    count: int = 0


# ---------------------------------------------------------------------------
# Batch result models
# ---------------------------------------------------------------------------


class BatchCreatedItem(BaseModel):
    """A successfully created lead in a batch create response."""

    model_config = ConfigDict(populate_by_name=True)

    index: int
    id: str
    created_at: int | None = None


class BatchError(BaseModel):
    """A failed item in a batch operation."""

    model_config = ConfigDict(populate_by_name=True)

    index: int
    message: str


class BatchCreateResult(BaseModel):
    """Result of a batch lead creation.

    Attributes:
        created: Successfully created items.
        errors: Failed items.
        total: Total number of leads in the request.
        success: Number of successfully created leads.
        failed: Number of failed leads.
    """

    model_config = ConfigDict(populate_by_name=True)

    created: list[BatchCreatedItem] = Field(default_factory=list)
    errors: list[BatchError] = Field(default_factory=list)
    total: int = 0
    success: int = 0
    failed: int = 0


class BatchResultItem(BaseModel):
    """A single result entry in a batch update or delete response."""

    model_config = ConfigDict(populate_by_name=True)

    index: int
    id: str
    success: bool
    message: str | None = None


class BatchResult(BaseModel):
    """Result of a batch update or delete operation.

    Attributes:
        results: Per-item outcomes.
        total: Total number of leads in the request.
        success: Number of successfully processed leads.
        failed: Number of failed leads.
    """

    model_config = ConfigDict(populate_by_name=True)

    results: list[BatchResultItem] = Field(default_factory=list)
    total: int = 0
    success: int = 0
    failed: int = 0


# ---------------------------------------------------------------------------
# Attribute helpers
# ---------------------------------------------------------------------------


def text_attr(name: str, value: str) -> Attribute:
    """Create a text-typed custom attribute.

    Args:
        name: Attribute name.
        value: String value.

    Returns:
        An :class:`Attribute` with ``type="text"``.
    """
    return Attribute(name=name, type="text", value=value)


def number_attr(name: str, value: float) -> Attribute:
    """Create a number-typed custom attribute.

    Args:
        name: Attribute name.
        value: Numeric value.

    Returns:
        An :class:`Attribute` with ``type="number"``.
    """
    return Attribute(name=name, type="number", value=value)


def bool_attr(name: str, value: bool) -> Attribute:
    """Create a boolean-typed custom attribute.

    Args:
        name: Attribute name.
        value: Boolean value.

    Returns:
        An :class:`Attribute` with ``type="bool"``.
    """
    return Attribute(name=name, type="bool", value=value)


def list_attr(name: str, value: list[str]) -> Attribute:
    """Create a list-typed custom attribute.

    Args:
        name: Attribute name.
        value: List of strings.

    Returns:
        An :class:`Attribute` with ``type="list"``.
    """
    return Attribute(name=name, type="list", value=value)


def object_attr(name: str, value: dict[str, Any]) -> Attribute:
    """Create an object-typed custom attribute.

    Args:
        name: Attribute name.
        value: Dictionary value.

    Returns:
        An :class:`Attribute` with ``type="object"``.
    """
    return Attribute(name=name, type="object", value=value)


# ---------------------------------------------------------------------------
# ListOptions builder
# ---------------------------------------------------------------------------


class ListOptions:
    """Reusable query builder for lead list operations.

    Supports method chaining. Instances are immutable — each ``with_*`` call
    returns a new :class:`ListOptions` instance.

    Example::

        opts = (
            ListOptions()
            .with_limit(50)
            .with_sort(SortField.RATING, SortOrder.DESC)
            .with_filter(city().eq("Berlin"))
        )
        result = client.list(options=opts)
        next_result = client.list(options=opts.with_cursor(result.next_cursor))
    """

    def __init__(self) -> None:
        self._filters: list[Any] = []
        self._sort_by: SortField | str | None = None
        self._sort_order: SortOrder | None = None
        self._limit: int | None = None
        self._cursor: str | None = None

    def _copy(self) -> "ListOptions":
        clone = ListOptions()
        clone._filters = list(self._filters)
        clone._sort_by = self._sort_by
        clone._sort_order = self._sort_order
        clone._limit = self._limit
        clone._cursor = self._cursor
        return clone

    def with_filter(self, filter_obj: Any) -> "ListOptions":
        """Add a filter to the query.

        Args:
            filter_obj: A filter object created by one of the filter helper
                functions (e.g. ``city().eq("Berlin")``).

        Returns:
            A new :class:`ListOptions` with the filter appended.
        """
        clone = self._copy()
        clone._filters.append(filter_obj)
        return clone

    def with_sort(self, sort_by: "SortField | str", sort_order: SortOrder | None = None) -> "ListOptions":
        """Set the sort field and optional direction.

        Args:
            sort_by: The field to sort by.
            sort_order: ``SortOrder.ASC`` or ``SortOrder.DESC``.

        Returns:
            A new :class:`ListOptions` with the sort settings applied.
        """
        clone = self._copy()
        clone._sort_by = sort_by
        clone._sort_order = sort_order
        return clone

    def with_limit(self, limit: int) -> "ListOptions":
        """Set the maximum number of results per page.

        Args:
            limit: Page size (1–1000).

        Returns:
            A new :class:`ListOptions` with the limit applied.
        """
        clone = self._copy()
        clone._limit = limit
        return clone

    def with_cursor(self, cursor: str | None) -> "ListOptions":
        """Set the pagination cursor.

        Args:
            cursor: Opaque cursor token from a previous :class:`ListResult`.

        Returns:
            A new :class:`ListOptions` with the cursor applied.
        """
        clone = self._copy()
        clone._cursor = cursor
        return clone
