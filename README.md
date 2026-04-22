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

## Authentication

Get your API token from the [Intelion Cloud dashboard](https://intelion.cloud). The client sends it as `Authorization: Token {token}`.

## Error handling

```python
from intelion_cloud import (
    AuthenticationError, NotFoundError, ConflictError,
    RateLimitError, ValidationError, ServerError,
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
