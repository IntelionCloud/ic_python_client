# ic_python_client — Python SDK для Intelion Cloud API

Standalone Python-клиент для REST API Intelion Cloud (`/api/v2/`). Не зависит от Django — чистый httpx.

## Стек

- **Python 3.9+**, единственная runtime-зависимость — `httpx>=0.24`
- **Dev:** pytest + pytest-asyncio + respx
- **Сборка:** setuptools (pyproject.toml), пакет `intelion-cloud` (версию смотреть в `pyproject.toml`, не дублировать её здесь — разъезжается)

## Структура

```
ic_python_client/
├── Dockerfile              # standalone-образ для тестов
├── pyproject.toml
├── intelion_cloud/
│   ├── __init__.py         # Public API: клиенты, модели, exceptions, enums
│   ├── _client.py          # IntelionCloud (sync), AsyncIntelionCloud (async)
│   ├── _transport.py       # SyncTransport / AsyncTransport (httpx + retry)
│   ├── _pagination.py      # PaginatedResponse[T], auto-pagination helpers
│   ├── constants.py        # Enums: ServerStatus, ServerState, PricePlan, BillingPeriod, OSType
│   ├── exceptions.py       # Иерархия ошибок (APIError → Auth/Forbidden/NotFound/...)
│   ├── models/
│   │   ├── _base.py        # _get(), _parse_nested(), _parse_nested_list()
│   │   ├── components.py   # GPU, CPU, RAM, SSD, OSImage, SoftwareAddon
│   │   ├── flavors.py      # Flavor, FlavorSubstitution
│   │   ├── ssh_keys.py     # SSHKey
│   │   ├── servers.py      # CloudServer, UsageAct, DebtInfo, Promocode, WhiteIP, ServerStatus, PhysicalServer, SoftwareAddonInstance
│   │   └── users.py        # User
│   └── resources/
│       ├── _base.py        # SyncResource / AsyncResource (HTTP-методы, пагинация)
│       ├── cloud_servers.py# CloudServers / AsyncCloudServers
│       ├── catalog.py      # GPUs / CPUs / RAMs / SSDs / SoftwareAddons (+Async)
│       ├── flavors.py      # Flavors / AsyncFlavors
│       ├── ssh_keys.py     # SSHKeys / AsyncSSHKeys
│       ├── os_images.py    # OSImages / AsyncOSImages
│       └── users.py        # Users / AsyncUsers
└── tests/
    ├── conftest.py         # Fixtures, SAMPLE_* данные
    ├── test_client.py      # Init, context manager, resources attached
    ├── test_transport.py   # Error mapping (401→AuthenticationError, ...), retry logic
    ├── test_models.py      # from_dict() для всех моделей
    ├── test_cloud_servers.py # CRUD, actions, pagination, clone, migrate
    ├── test_flavors.py     # list()
    └── test_users.py       # me(), get(), update()
```

## Архитектура

### Слои

```
IntelionCloud / AsyncIntelionCloud       ← точка входа, создаёт ресурсы
    ↓
    Resources (CloudServers, Flavors, OSImages, Users)  ← бизнес-методы (list, get, create, start, ...)
    ↓
    SyncResource / AsyncResource         ← _get(), _post(), _patch(), _list_all(), _list_page()
    ↓
    SyncTransport / AsyncTransport       ← httpx.Client, retry, error mapping
```

### Транспорт (_transport.py)

- **Base URL:** `{base_url}/api/v2/` (default: `https://intelion.cloud/api/v2/`)
- **Auth:** заголовок `Authorization: Token {token}`
- **Timeout:** 30s overall, 10s connect (настраивается)
- **Retry:**
  - 429 Rate Limit → до 3 ретраев, exponential backoff (или Retry-After), **включая POST**
  - 5xx Server Error → 1 ретрай, **только идемпотентные** (GET/PUT/PATCH/DELETE)
  - Connection/Timeout → 2 ретрая, только идемпотентные

### Пагинация (_pagination.py)

DRF-совместимая: `count`, `next`, `previous`, `results`.

- `resource.list()` (без page) → auto-paginate: обходит все страницы, возвращает `List[Model]`
- `resource.list(page=N)` → одна страница `PaginatedResponse[Model]` с `.has_next`, `.count`
- `extract_next_page()` — парсит absolute URL из `next`, достаёт relative path + params

### Модели

Все модели — `@dataclass(frozen=True)` (immutable). Десериализация через `Model.from_dict(data)`.

Хелперы в `_base.py`:
- `_get(data, key)` — как `dict.get()`, но `""` → `None`
- `_parse_nested(data, key, cls)` — вложенный объект → `cls.from_dict()`
- `_parse_nested_list(data, key, cls)` — список вложенных объектов

### Exceptions

```
IntelionCloudError (base)
├── APIError (status_code, response_body)
│   ├── AuthenticationError    # 401
│   ├── ForbiddenError         # 403
│   ├── NotFoundError          # 404
│   ├── ConflictError          # 409 (сервер занят операцией)
│   ├── RateLimitError         # 429 (+retry_after)
│   ├── ValidationError        # 400 (+field_errors dict)
│   └── ServerError            # 5xx
└── ConnectionError            # сетевой уровень
```

`_extract_message()` ищет ключи `detail`, `message`, `error`, `non_field_errors` в теле ответа.

### Enums (constants.py)

| Enum | Значения |
|------|----------|
| `ServerStatus` | ERROR=-4, DELETED=-3, REQUESTED=-2, PAUSED=-1, PAUSING=0, START=1, ACTIVE=2, PREPARING=3 |
| `ServerState` | IDLE=0, STARTING=100, SHELVING=200, MIGRATING_*=301-304, CLONING=400, QUEUED=500, AWAITING_PASSWORD=600, MAINTENANCE=700 |
| `PricePlan` | POSTPAID_QUARTER=-3, POSTPAID_MONTHLY=-1, HOURLY=0, MONTHLY=1, QUARTERLY=3, SEMIANNUAL=6, ANNUAL=12 |
| `BillingPeriod` | HOURLY=0, MONTHLY=30, MONTHLY_ALIGNED=31 |
| `OSType` | WINDOWS="win", LINUX="lin" |

## API-эндпоинты

| Ресурс | Метод | Endpoint | Описание |
|--------|-------|----------|----------|
| **CloudServers** | `list()` | GET `cloud-servers/` | Список серверов (auto-paginate) |
| | `get(id)` | GET `cloud-servers/{id}/` | Один сервер |
| | `create(...)` | POST `cloud-servers/` | Создать сервер (canonical) |
| | `update(id, ...)` | PATCH `cloud-servers/{id}/` | Обновить имя / auto_renewal |
| | `start(id)` | POST `cloud-servers/{id}/actions/` | Запустить (status=2) |
| | `stop(id)` | POST `cloud-servers/{id}/actions/` | Остановить (status=-1) |
| | `reboot(id)` | POST `cloud-servers/{id}/actions/` | Перезагрузить (status="REBOOT") |
| | `delete(id)` | POST `cloud-servers/{id}/actions/` | Удалить (status=-3) |
| | `get_status(id)` | GET `cloud-servers/{id}/status/` | Можно ли запустить + affordable_runtime |
| | `get_password(id)` | GET `cloud-servers/{id}/password/` | Пароль Windows |
| | `clone(id)` | POST `cloud-servers/{id}/clone/` | Клонировать |
| | `migrate(id, flavor_id, price_plan)` | POST `cloud-servers/{id}/migrate/` | Мигрировать (FlavorConfig PK + price_plan) |
| **Flavors** | `list()` | GET `flavors/` | Список flavors |
| **OSImages** | `list(flavor_id= / gpu_id=)` | GET `os-images/` | ОС-образы (фильтр по FlavorConfig или GPU) |
| **Users** | `me()` | GET `users/` | Текущий пользователь (первый в списке) |
| | `get(id)` | GET `users/{id}/` | Пользователь по ID |
| | `update(id, ...)` | PATCH `users/{id}/` | Обновить профиль |
| **SSHKeys** | `list()` | GET `ssh-keys/` | Ключи аккаунта. ⚠️ Голый массив, не DRF-конверт — `page` тут нет |
| | `create(public_key, name=)` | POST `ssh-keys/` | 400 — ключ невалиден/слабый RSA, 409 — такой fingerprint уже есть |
| | `delete(id)` | DELETE `ssh-keys/{id}/` | 204; чужой ключ → 404 |
| **GPUs/CPUs/RAMs/SSDs** | `list(page=)`, `get(id)` | GET `gpus/`, `cpus/`, `ram/`, `ssds/` | Каталог, `PageNumberPagination` |
| **SoftwareAddons** | `list()`, `get(id)` | GET `software-addons/` | ⚠️ `LimitOffsetPagination` — `page` НЕ поддерживается |

## Тесты

**86 тестов**, все проходят в Docker.

### Запуск

```bash
cd ic_python_client
docker build -t ic-python-client-test .
docker run --rm ic-python-client-test
```

### Паттерны тестирования

- **respx** — мок httpx-запросов. Используется декоратор `@respx.mock(base_url=API_URL)`.
- **SAMPLE_* константы** в `conftest.py` — полные JSON-ответы API для каждой модели.
- Тесты sync-only (async-клиент покрыт только init/context manager).

### Известная ловушка: respx и auto-pagination

**respx матчит роуты по порядку регистрации.** Роут `get("path/")` без params ловит ВСЕ запросы к этому path, включая `?page=2`. Для тестов пагинации использовать `side_effect` со списком ответов:

```python
respx_mock.get("cloud-servers/").mock(
    side_effect=[
        httpx.Response(200, json={...first_page...}),
        httpx.Response(200, json={...second_page...}),
    ]
)
```

НЕ работает (бесконечный цикл):
```python
respx_mock.get("cloud-servers/").respond(200, json={...next: "?page=2"...})
respx_mock.get("cloud-servers/", params={"page": "2"}).respond(200, json={...})
# ↑ второй mock никогда не сработает — первый перехватывает всё
```

## Соответствие серверному API

Модели клиента зеркалят сериализаторы DRF из `website/user_panel/` и `website/servers/`:

| Клиентская модель | DRF Serializer (серверный) |
|---|---|
| `CloudServer` | `CloudServerSerializer` (user_panel) |
| `Flavor` | `FlavorConfigSerializer` (servers) |
| `GPU/CPU/RAM/SSD` | `GPUSerializer`, `CPUSerializer`, etc. (servers) |
| `User` | `ICUserSerializer` (user_panel) |
| `UsageAct` | `UsageActSerializer` (user_panel) |
| `OSImage` | `OSImageSerializer` (servers) |

**Ключевое отличие:** `CloudServer.flavor_oid` — cloud vs dedicated discriminator (NULL = dedicated). Совпадает с `UserConfiguration.flavor_oid` на сервере.

## Важные контракты API v2

- **`create()` → POST `cloud-servers/`** (canonical). Старый `server-orders/` теперь GET-only (deep-link handler).
- **`create()` payload**: `{name, flavor_id (int PK FlavorConfig), ssd_count (min 30 GB), os_id, price_plan, promocode_id?, is_in_queue?, addon_ids?}`. CPU/RAM/GPU фиксируются флейвором — отдельно не передаются.
- **`migrate()` payload**: `{flavor_id (int), price_plan}`. CPU/RAM/GPU тоже из флейвора.
- **OSImage.compatible_flavor_ids** — список совместимых FlavorConfig. Пустой список = универсальный образ. (Раньше было `compatible_gpu_ids` — переименовано на сервере.)
- **Фильтры OSImages**: `flavor_id` (точно) или `gpu_id` (через flavor.gpu_id). Без фильтра — только универсальные образы.
- **`queue_disabled` + `suggested_alternative`** (есть и у `Flavor`, и у `CloudServer`) — карта в долгосрочной аренде, очередь на неё сервер отбивает **409**. `suggested_alternative` (модель `FlavorSubstitution`) заполняется ТОЛЬКО когда `queue_disabled` И `max_available == 0`; при наличии ёмкости там `None` — сервер не гоняет подбор замены зря. Поле `exact_match=False` значит, что точного эквивалента по cpu/ram на карте-замене нет и подобран ближайший.
- **`CloudServer.password_rotation`** (модель `PasswordRotation`) — свершившийся факт ротации root-пароля (инцидент 2026-07-29). Статус `PENDING` наружу не отдаётся принципиально, наружу приходит только `rotated`/`failed`. `acknowledged` живёт на сервере, а не в клиенте.
- **⚠️ Две РАЗНЫЕ пагинации в одном API.** Каталог железа (`gpus/`, `cpus/`, `ram/`, `ssds/`) — `PageNumberPagination` (`?page=N`), а `software-addons/` — `LimitOffsetPagination` (`?limit=&offset=`). DRF молча игнорирует `?page=N` на limit/offset-эндпоинте и отдаёт первую страницу — то есть ошибка выглядит как «данные есть, просто не те». Поэтому у `SoftwareAddons.list()` параметра `page` нет вовсе, а auto-paginate везде идёт по URL из `next`, а не конструирует параметры сам.
- **⚠️ `ssh-keys/` — не ViewSet.** Обычный `APIView`: GET отдаёт голый JSON-массив без `{count, next, previous, results}`. `parse_paginated()` такой ответ переварит, но `page`-аргумента у ресурса нет и быть не может. Плюс rate limit 30/мин на юзера → `RateLimitError`.
- **⚠️ OpenAPI-схема врёт про типы этих полей.** drf-spectacular типизирует любой `SerializerMethodField` как `string`, поэтому в `/api/schema/` `queue_disabled` числится строкой, а `suggested_alternative` и `password_rotation` — тоже строками. Реально это `bool` и два вложенных объекта. Сверять с сериализаторами (`website/servers/serializers.py`, `website/user_panel/serializers.py`), а не со схемой.

## Добавление нового ресурса

1. Создать модель в `models/` — frozen dataclass с `from_dict()`
2. Экспортировать из `models/__init__.py`
3. Создать sync + async resource-классы в `resources/` (наследуют `SyncResource`/`AsyncResource`)
4. Экспортировать из `resources/__init__.py`
5. Подключить к клиенту в `_client.py` (обоим: `IntelionCloud` и `AsyncIntelionCloud`)
6. Экспортировать из `__init__.py`
7. Написать тесты с respx-моками и SAMPLE_* данными в conftest

## Release process

**Релиз автоматизирован через GitHub Actions + PyPI Trusted Publishing (OIDC).** Триггер — git-тег `vX.Y.Z`. Никаких токенов/секретов в репозитории не требуется: PyPI валидирует релиз по GitHub OIDC claim (owner/repo/workflow). Фейловер через ручной токен описан в секции "Fallback".

### Когда делать релиз

**Обязательно** — после любого изменения публичного API v2 в `client_board`, которое затронуло клиент (см. правило "API v2 ↔ ic_python_client sync" в `client_board/CLAUDE.md`). Внешние пользователи SDK должны получить обновление, иначе клиент тихо отстаёт от сервера.

**По SemVer:**
- `MAJOR` (0.x → 1.0, 1.x → 2.0) — ломающие изменения публичного API клиента. Любое изменение сигнатуры публичного метода, переименование/удаление поля модели, изменение endpoint/payload — это breaking для потребителя SDK.
- `MINOR` (0.2 → 0.3) — новые ресурсы/методы/поля без ломки существующих.
- `PATCH` (0.2.0 → 0.2.1) — багфиксы, обновление README/docs (PyPI-описание обновляется только при новой версии — артефакты на PyPI иммутабельны).

### Как выпустить новую версию

1. **Закоммитить все изменения в `main`** (включая тесты, которые должны быть зелёные).

2. **Бампнуть версию в ДВУХ местах синхронно:**
   - `pyproject.toml` → `version = "X.Y.Z"`
   - `intelion_cloud/__init__.py` → `__version__ = "X.Y.Z"`

   Release workflow валидирует соответствие тега обоим файлам — если не совпадает, релиз упадёт.

3. **Закоммитить bump:**
   ```bash
   git add pyproject.toml intelion_cloud/__init__.py
   git commit -m "Release vX.Y.Z"
   git push origin main
   ```

4. **Создать и запушить тег:**
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z: <короткое описание>"
   git push origin vX.Y.Z
   ```

5. **Ждать CI.** GitHub Actions автоматически:
   - Прогонит `pytest` на Python 3.12.
   - Соберёт `sdist + wheel`.
   - Проверит `twine check`.
   - Зальёт на PyPI через OIDC (job `publish`, environment `pypi`).
   - Создаст GitHub Release с авто-сгенерированным changelog'ом и приложит артефакты.

   Прогресс: https://github.com/IntelionCloud/ic_python_client/actions

6. **Проверить:** `pip install --upgrade intelion-cloud` в чистом venv должен подтянуть новую версию через 1-2 минуты после окончания workflow.

### Trusted Publishing: как настроено

На https://pypi.org/manage/project/intelion-cloud/settings/publishing/ (именно **project-level**, не profile) зарегистрирован publisher:
- **Owner:** `IntelionCloud`
- **Repository:** `ic_python_client`
- **Workflow:** `release.yml`
- **Environment:** `pypi`

На GitHub создан environment `pypi` (https://github.com/IntelionCloud/ic_python_client/settings/environments) — без required reviewers, просто держит имя для OIDC-claim. Если захочется manual approval перед публикацией, включи там required reviewers.

В `release.yml` → job `publish`:
```yaml
environment:
  name: pypi
  url: https://pypi.org/project/intelion-cloud/
permissions:
  id-token: write
steps:
  - uses: pypa/gh-action-pypi-publish@release/v1
```
Никаких `password:`, `PYPI_API_TOKEN`, секретов — OIDC-токен выпускается GitHub'ом при выполнении job и обменивается на короткоживущий upload-токен PyPI.

### Fallback: ручной релиз через токен

Обычно не нужен — OIDC работает. Если CI сломался и нужно срочно:

1. Создать одноразовый API-токен на https://pypi.org/manage/account/token/ (scope: `Project: intelion-cloud`, не entire account).
2. Собрать и залить локально:
   ```bash
   cd ic_python_client
   rm -rf build/ dist/ *.egg-info
   python -m build
   twine check dist/*
   TWINE_USERNAME=__token__ TWINE_PASSWORD='pypi-AgEI...' twine upload dist/*
   ```
3. Сразу после релиза — revoke токен на PyPI. Не хранить в `credentials.md` или секретах.

### CI / тесты

Отдельный workflow `test.yml` прогоняет pytest на матрице Python 3.9–3.13 на каждый push в `main` и каждый PR. Если тесты красные — релиз-workflow всё равно провалится (он запускает тесты заново перед билдом), но лучше ловить это до тега.
