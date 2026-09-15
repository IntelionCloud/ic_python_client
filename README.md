# Intelion Cloud Python Client

[![PyPI](https://img.shields.io/pypi/v/intelion-cloud.svg)](https://pypi.org/project/intelion-cloud/)
[![Python](https://img.shields.io/pypi/pyversions/intelion-cloud.svg)](https://pypi.org/project/intelion-cloud/)
[![License](https://img.shields.io/pypi/l/intelion-cloud.svg)](https://github.com/IntelionCloud/ic_python_client/blob/main/LICENSE)

Official Python SDK for the [Intelion Cloud](https://intelion.cloud) GPU cloud API (`/api/v2/`).

Sync and async clients, typed dataclass models, automatic pagination, retries with exponential backoff.

## Install

```bash
pip install intelion-cloud
```

Requires Python 3.9+.

## Quickstart

```python
from intelion_cloud import IntelionCloud

client = IntelionCloud(token="your_api_token")

# List your cloud servers
for server in client.cloud_servers.list():
    print(server.id, server.name, server.status)

# Start / stop a server
client.cloud_servers.start(server_id=42)
client.cloud_servers.stop(server_id=42)

# Create a new server
new_server = client.cloud_servers.create(
    name="my-h100-box",
    flavor_id=1,          # FlavorConfig PK
    ssd_count=100,        # network disk size, GB (min 30)
    os_id=1,              # OperationalSystemImage PK
    price_plan=0,         # 0 = hourly, 1 = monthly, ...
)

client.close()
```

### Async client

```python
import asyncio
from intelion_cloud import AsyncIntelionCloud

async def main():
    async with AsyncIntelionCloud(token="your_api_token") as client:
        me = await client.users.me()
        print(me.username, me.current_balance_rub_cents)

asyncio.run(main())
```

### Context manager

```python
with IntelionCloud(token="...") as client:
    servers = client.cloud_servers.list()
```

## Available resources

| Resource | Methods |
|---|---|
| `client.cloud_servers` | `list()`, `get()`, `create()`, `update()`, `start()`, `stop()`, `reboot()`, `delete()`, `get_status()`, `get_password()`, `clone()`, `migrate()` |
| `client.flavors` | `list()` |
| `client.os_images` | `list(flavor_id=, gpu_id=)` |
| `client.users` | `me()`, `get()`, `update()` |
| `client.ssh_keys` | `list()`, `create(public_key, name=)`, `delete(key_id)` |
| `client.gpus` / `client.cpus` / `client.ram` / `client.ssds` | `list(page=)`, `get(id)` |
| `client.software_addons` | `list()`, `get(id)` |
| `client.inference_api_keys` | `list()`, `get()`, `create()`, `update()`, `revoke()`, `rotate()`, `usage()`, `usage_range()`, `usage_range_csv()`, `models()`, `access_status()`, `request_access()` |

## AI API keys

Keys for LLM inference (`https://aiapi.intelion.cloud/v1/...`) — **not** the
same thing as your main `token` above, which authenticates every call in
this SDK. AI API is self-serve, gated on account balance:

```python
status = client.inference_api_keys.access_status()
if not status.granted:
    print(f"Не хватает {status.shortfall_rub_cents / 100:.2f} ₽")
    client.inference_api_keys.request_access()  # raises PaymentRequiredError if still short

key = client.inference_api_keys.create(name="prod-agent", rate_limit_rpm=60)
print(key.api_key)  # raw value — shown ONLY here, persist it now

usage = client.inference_api_keys.usage_range(date_from="2026-05-01", date_to="2026-05-31")
print(usage.total_rub_cents)  # reconciles with «История операций» for the same range

# Replace the key's value without losing its usage history; the old value
# keeps working for grace_period_hours (default 24, 0 = retire immediately).
rotated = client.inference_api_keys.rotate(key.key_hash, grace_period_hours=24)
print(rotated.new_key.api_key)
```

## Usage act costs

Every usage act (`server.usage_act`, `last_usage_act`, `last_finished_usage_act`,
`resume_usage_act`) carries server-computed costs in kopecks: `next_charge_rub_cents`
(the next debit), `full_period_cost_rub_cents` (current period incl. prepay) and
`full_planned_cost_rub_cents` (stand-alone price of the planned period, the number
to show in a "confirm start" dialog), plus the act's own `discount_percent` and the
applied `promocode_code` / `promocode_discount_value`. Do not recompute them
client-side.

## Cold storage

A stopped server keeps its boot volume for free for a while (`cold_free` says
until when and at what price after), then the compute is released and the
volume is billed as cold storage (`cold_storage`). Both blocks are `None` on a
running server; `resume_usage_act` is the server-side price of resuming a cold
server.

```python
from intelion_cloud import ServerState

server = client.cloud_servers.get(42)
if server.server_state in (ServerState.COLD_STORAGE, ServerState.COLD_GRACE):
    print(f"{server.cold_storage.storage_gb} GB, debt {server.cold_storage.accrued_debt_rub_cents} kopecks")
    print(f"resume costs {server.resume_usage_act.next_payment.amount_rub_cents} kopecks")
elif server.cold_free:
    print(f"free storage until {server.cold_free.free_until_dt}")
```

## Rental term

Servers on a term plan (`price_plan` 3, 6 or 12 months) carry a read-only
snapshot of the commitment: `term_months`, `term_discount_percent`,
`term_started_at`, `term_ends_at` (already shifted by any downtime on our side),
`term_state` and the flags the server derives from them.

```python
from intelion_cloud import TermState

server = client.cloud_servers.get(42)
if server.term_state == TermState.ACTIVE:
    print(f"{server.term_months} months at -{server.term_discount_percent}% until {server.term_ends_at}")
if server.is_bound_by_term:
    # PATCH is_auto_renewal=False is refused with 400 (ValidationError) until the term ends
    ...
```

Consent, renewal and early termination are personal-account actions and are
not part of API v2; the SDK only reads their state.

## Authentication

Get your API token from the [Intelion Cloud dashboard](https://intelion.cloud). The client sends it as `Authorization: Token {token}`.

## Error handling

```python
from intelion_cloud import (
    AuthenticationError, NotFoundError, ConflictError,
    RateLimitError, ValidationError, ServerError, PaymentRequiredError,
)

try:
    server = client.cloud_servers.get(999)
except NotFoundError:
    print("Server not found")
except AuthenticationError:
    print("Invalid token")
except ValidationError as e:
    print("Field errors:", e.field_errors)
```

## Links

- **Homepage:** https://intelion.cloud
- **API docs (Swagger):** https://intelion.cloud/api/
- **Source:** https://github.com/IntelionCloud/ic_python_client

## License

MIT
