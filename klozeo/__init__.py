"""Klozeo Python SDK.

Official Python client for the Klozeo Lead Management API.

Quick start::

    from klozeo import Klozeo, Lead

    client = Klozeo("sk_live_your_api_key")

    # Create a lead
    resp = client.create(Lead(name="Acme Corporation", source="website"))
    print(f"Created: {resp.id}")

    # List with filters
    from klozeo import city, rating, SortField, SortOrder

    result = client.list(
        city().eq("Berlin"),
        rating().gte(4.0),
        sort_by=SortField.RATING,
        sort_order=SortOrder.DESC,
        limit=20,
    )

    # Iterate all pages automatically
    for lead in client.iterate(city().eq("Berlin")):
        print(lead.name)

Async client::

    import asyncio
    from klozeo import AsyncKlozeo, Lead

    async def main():
        async with AsyncKlozeo("sk_live_your_api_key") as client:
            resp = await client.create(Lead(name="Acme", source="website"))

    asyncio.run(main())
"""

from ._async_client import AsyncKlozeo
from ._client import Klozeo
from ._errors import (
    BadRequestError,
    ForbiddenError,
    KlozeoError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
    ValidationError,
)
from ._filters import (
    Filter,
    attr,
    attr_sort_field,
    category,
    city,
    country,
    email,
    location,
    name,
    or_,
    phone,
    rating,
    review_count,
    source,
    state,
    tags,
    website,
)
from ._models import (
    Attribute,
    BatchCreateResult,
    BatchCreatedItem,
    BatchError,
    BatchResult,
    BatchResultItem,
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
    bool_attr,
    list_attr,
    number_attr,
    object_attr,
    text_attr,
)

__all__ = [
    # Clients
    "Klozeo",
    "AsyncKlozeo",
    # Models
    "Lead",
    "UpdateLeadInput",
    "Note",
    "Attribute",
    "ScoringRule",
    "ScoringRuleInput",
    "Webhook",
    "WebhookInput",
    "CreateResponse",
    "ListResult",
    "BatchResult",
    "BatchCreateResult",
    "BatchCreatedItem",
    "BatchError",
    "BatchResultItem",
    # Enums
    "ExportFormat",
    "SortField",
    "SortOrder",
    # Query builder
    "ListOptions",
    "Filter",
    # Filter factory functions
    "city",
    "name",
    "country",
    "state",
    "category",
    "source",
    "email",
    "phone",
    "website",
    "rating",
    "review_count",
    "tags",
    "location",
    "attr",
    "or_",
    "attr_sort_field",
    # Attribute helpers
    "text_attr",
    "number_attr",
    "bool_attr",
    "list_attr",
    "object_attr",
    # Errors
    "KlozeoError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "RateLimitedError",
    "BadRequestError",
    "ValidationError",
]

__version__ = "0.1.0"
