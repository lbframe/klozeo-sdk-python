# Klozeo Python SDK

Official Python client for the [Klozeo](https://klozeo.com) Lead Management API.

## Installation

```bash
pip install klozeo
```

Requires Python 3.10+.

## Quick Start

```python
from klozeo import Klozeo, Lead

client = Klozeo("sk_live_your_api_key")

# Create a lead
resp = client.create(Lead(
    name="Acme Corporation",
    source="website",
    city="San Francisco",
    email="contact@acme.com",
    rating=4.5,
    tags=["enterprise", "saas"],
))
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
for lead in result.leads:
    print(f"{lead.name} — score: {lead.score}")

# Paginate automatically
for lead in client.iterate(city().eq("Berlin")):
    print(lead.name)
```

## Async Client

```python
import asyncio
from klozeo import AsyncKlozeo, Lead

async def main():
    async with AsyncKlozeo("sk_live_your_api_key") as client:
        resp = await client.create(Lead(name="Acme", source="website"))
        async for lead in client.iterate(city().eq("Berlin")):
            print(lead.name)

asyncio.run(main())
```

## Error Handling

```python
from klozeo import NotFoundError, RateLimitedError, ForbiddenError, KlozeoError

try:
    lead = client.get("cl_nonexistent")
except NotFoundError:
    print("Lead not found")
except RateLimitedError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except ForbiddenError:
    print("Leads limit reached — upgrade your plan")
except KlozeoError as e:
    print(f"HTTP {e.status_code}: {e.message}")
```

## Links

- Documentation: https://docs.klozeo.com
- API Reference: https://docs.klozeo.com/api/leads
- PyPI: https://pypi.org/project/klozeo
