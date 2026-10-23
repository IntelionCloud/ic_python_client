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
├── CHANGELOG.md            # заметки к версиям (с 0.7.0)
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
│   │   ├── servers.py      # CloudServer, UsageAct, DebtInfo, Promocode, WhiteIP, ServerStatus, DiskExtendOrder, PhysicalServer, SoftwareAddonInstance
│   │   ├── users.py        # User, ColdStorageSummary
│   │   └── inference_api_keys.py # InferenceApiKey, RotatedInferenceApiKey, InferenceApiKeyUsage, InferenceApiUsageRange, InferenceApiAccessStatus
│   └── resources/
│       ├── _base.py        # SyncResource / AsyncResource (HTTP-методы, пагинация, _delete/_get_text)
│       ├── cloud_servers.py# CloudServers / AsyncCloudServers
│       ├── catalog.py      # GPUs / CPUs / RAMs / SSDs / SoftwareAddons (+Async)
│       ├── flavors.py      # Flavors / AsyncFlavors
│       ├── ssh_keys.py     # SSHKeys / AsyncSSHKeys
│       ├── os_images.py    # OSImages / AsyncOSImages
│       ├── users.py        # Users / AsyncUsers
│       └── inference_api_keys.py # InferenceApiKeys / AsyncInferenceApiKeys — AI API key CRUD + rotate + usage
└── tests/
    ├── conftest.py         # Fixtures, SAMPLE_* данные
    ├── test_client.py      # Init, context manager, resources attached
    ├── test_transport.py   # Error mapping (401→AuthenticationError, ...), retry logic
    ├── test_models.py      # from_dict() для всех моделей
    ├── test_cloud_servers.py # CRUD, actions, pagination, clone, migrate
    ├── test_flavors.py     # list()
    ├── test_users.py       # me(), get(), update()
    └── test_inference_api_keys.py # AI API keys: CRUD, rotate, usage, usage_range(+csv), access gate
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
│   ├── ConflictError          # 409: сервер занят, очередь запрещена (`reason`), отказ по сроку аренды (`error_code`)
│   ├── RateLimitError         # 429 (+retry_after)
│   ├── ValidationError        # 400 (+field_errors dict)
│   └── ServerError            # 5xx
└── ConnectionError            # сетевой уровень
```

`_extract_message()` ищет ключи `detail`, `message`, `error`, `non_field_errors` в теле ответа.
Машинные ярлыки тела читаются свойствами `APIError`: `reason` (отказы `POST cloud-servers/`) и `error_code` (отказы по сроку аренды, `TermConflictCode`), оба `None`, если ключа нет.

### Enums (constants.py)

| Enum | Значения |
|------|----------|
| `ServerStatus` | ERROR=-4, DELETED=-3, REQUESTED=-2, PAUSED=-1, PAUSING=0, START=1, ACTIVE=2, PREPARING=3 |
| `ServerState` | IDLE=0, STARTING=100, SHELVING=200, MIGRATING_*=301-304, DISK_EXTENDING=350, DISK_EXTENDING_ON_START=360, CLONING=400, QUEUED=500, AWAITING_PASSWORD=600, MAINTENANCE=700, CLEANUP_IN_PROGRESS=800, REINSTALLING=900, COLD_MOVING=950 (ещё НЕ в хранении), COLD_STORAGE=1000, COLD_GRACE=1100 |
| `PricePlan` | POSTPAID_QUARTER=-3, POSTPAID_MONTHLY=-1, HOURLY=0, MONTHLY=1, QUARTERLY=3, SEMIANNUAL=6, ANNUAL=12 |
| `BillingPeriod` | HOURLY=0, MONTHLY=30, MONTHLY_ALIGNED=31 |
| `OSType` | WINDOWS="win", LINUX="lin" |
| `TermConflictCode` | AUTO_RENEWAL_CONSENT_REQUIRED, AUTO_RENEWAL_NOT_APPLICABLE, TERM_RENEWAL_IN_PROGRESS, TERM_CONDITIONS_REQUIRED, LEGAL_TYPE_REQUIRED, LEGACY_TERMS_CONSENT_REQUIRED, AFFORDABLE_LAUNCH_UNDER_TERM, TERM_TERMINATION_REQUIRED (строковые `error_code` 409/400-отказов по сроку, достижимые токеном; зеркало `user_panel.services.term_obligation`; панельные коды подписи в SDK не перечислены) |
| `TermState` | NOT_TERM_PLAN="not_term_plan", ACTIVE="active", PENDING_CONSENT="pending_consent", GRANDFATHERED="grandfathered", LEGACY_EXPIRED="legacy_expired", CONFIRMED_EXPIRED="confirmed_expired", NO_SNAPSHOT="no_snapshot" (главное значение для неподписанного черновика и сервера после смены тарифа; строковые коды `CloudServer.term_state`, зеркало `user_panel.consts.TermState`; правила срока действуют с даты включения новой редакции оферты; конкретную дату в SDK не пишем, она живёт в настройке сервера `IC_PRICING_REFORM_EFFECTIVE_DT`) |

## API-эндпоинты

| Ресурс | Метод | Endpoint | Описание |
|--------|-------|----------|----------|
| **CloudServers** | `list()` | GET `cloud-servers/` | Список серверов (auto-paginate) |
| | `get(id)` | GET `cloud-servers/{id}/` | Один сервер |
| | `create(...)` | POST `cloud-servers/` | Создать сервер (canonical); `ssh_key_ids` — ключи в добавок к паролю |
| | `update(id, ...)` | PATCH `cloud-servers/{id}/` | Обновить имя / auto_renewal (под сроком включение 409, см. контракты) |
| | `start(id)` | POST `cloud-servers/{id}/actions/` | Запустить (status=2); под сроком `is_auto_renewal` игнорируется |
| | `stop(id)` | POST `cloud-servers/{id}/actions/` | Остановить (status=-1) |
| | `reboot(id)` | POST `cloud-servers/{id}/actions/` | Перезагрузить (status="REBOOT") |
| | `delete(id)` | POST `cloud-servers/{id}/actions/` | Удалить (status=-3) |
| | `reinstall_os(id)` | POST `cloud-servers/{id}/reinstall-os/` | Переустановить ОС. Без открытого периода аренды это запуск: 409 `TERM_CONDITIONS_REQUIRED` / `TERM_RENEWAL_IN_PROGRESS` / `LEGACY_TERMS_CONSENT_REQUIRED`, 400 при нехватке денег |
| | `get_status(id)` | GET `cloud-servers/{id}/status/` | Можно ли запустить, affordable_runtime, `launch_required_rub_cents`, `launch_funds_rub_cents` |
| | `get_password(id)` | GET `cloud-servers/{id}/password/` | Пароль Windows |
| | `clone(id)` | POST `cloud-servers/{id}/clone/` | Клонировать |
| | `migrate(id, flavor_id, price_plan, ssd_count=)` | POST `cloud-servers/{id}/migrate/` | Мигрировать (FlavorConfig PK + price_plan); `ssd_count` — заказ объёма диска на следующий запуск |
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

**242 теста**, все проходят в Docker.

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
| `CloudServer` | `UserConfigurationSerializer` (user_panel; отдаётся `GET /api/v2/cloud-servers/`) |
| `Flavor` | `FlavorConfigSerializer` (servers) |
| `GPU/CPU/RAM/SSD` | `GPUSerializer`, `CPUSerializer`, etc. (servers) |
| `User` | `ICUserSerializer` (user_panel) |
| `UsageAct` | `UsageActShortSerializer` (user_panel; вложен в `usage_act`, `last_usage_act`, `last_finished_usage_act`, `resume_usage_act`) |
| `OSImage` | `OSImageSerializer` (servers) |

**Ключевое отличие:** `CloudServer.flavor_oid` — cloud vs dedicated discriminator (NULL = dedicated). Совпадает с `UserConfiguration.flavor_oid` на сервере.

## Важные контракты API v2

- **`create()` → POST `cloud-servers/`** (canonical). Старый `server-orders/` теперь GET-only (deep-link handler).
- **`create()` payload**: `{name, flavor_id (int PK FlavorConfig), ssd_count (128-2048 ГБ, шаг 128; `servers/consts.py` сервера), os_id, price_plan, promocode_id?, is_in_queue?, addon_ids?, ssh_key_ids?}`. CPU/RAM/GPU фиксируются флейвором — отдельно не передаются.
- **`migrate()` payload**: `{flavor_id (int), price_plan, ssd_count?}`. Только диск остановленному серверу с томом: передать ТЕКУЩИЕ flavor_id и price_plan, иначе 400 `change_one_at_a_time`; ещё 404 `feature_disabled`, 409 `not_draft`, `disk_operation_pending`, `TERM_TERMINATION_REQUIRED`. CPU/RAM/GPU тоже из флейвора.
- **OSImage.compatible_flavor_ids** — список совместимых FlavorConfig. Пустой список = универсальный образ. (Раньше было `compatible_gpu_ids` — переименовано на сервере.)
- **Фильтры OSImages**: `flavor_id` (точно) или `gpu_id` (через flavor.gpu_id). Без фильтра — только универсальные образы.
- **`queue_disabled` + `suggested_alternative`** (есть и у `Flavor`, и у `CloudServer`) — карта в долгосрочной аренде, очередь на неё сервер отбивает **409**. `suggested_alternative` (модель `FlavorSubstitution`) заполняется ТОЛЬКО когда `queue_disabled` И `max_available == 0`; при наличии ёмкости там `None` — сервер не гоняет подбор замены зря. Поле `exact_match=False` значит, что точного эквивалента по cpu/ram на карте-замене нет и подобран ближайший.
- **`CloudServer.password_rotation`** (модель `PasswordRotation`) — свершившийся факт ротации root-пароля (инцидент 2026-07-29). Статус `PENDING` наружу не отдаётся принципиально, наружу приходит только `rotated`/`failed`. `acknowledged` живёт на сервере, а не в клиенте.
- **⚠️ Две РАЗНЫЕ пагинации в одном API.** Каталог железа (`gpus/`, `cpus/`, `ram/`, `ssds/`) — `PageNumberPagination` (`?page=N`), а `software-addons/` — `LimitOffsetPagination` (`?limit=&offset=`). DRF молча игнорирует `?page=N` на limit/offset-эндпоинте и отдаёт первую страницу — то есть ошибка выглядит как «данные есть, просто не те». Поэтому у `SoftwareAddons.list()` параметра `page` нет вовсе, а auto-paginate везде идёт по URL из `next`, а не конструирует параметры сам.
- **⚠️ `ssh-keys/` — не ViewSet.** Обычный `APIView`: GET отдаёт голый JSON-массив без `{count, next, previous, results}`. `parse_paginated()` такой ответ переварит, но `page`-аргумента у ресурса нет и быть не может. Плюс rate limit 30/мин на юзера → `RateLimitError`.
- **Стоимость и скидка в `UsageAct` (`UsageActShortSerializer`, уже на `develop`).** 6 полей, которые SDK молча терял; все четыре денежных это `int` в копейках, считает бэк, в клиенте не пересчитывать:

  | Поле | Тип | Источник на сервере | Смысл |
  |---|---|---|---|
  | `next_charge_rub_cents` | `int`, дефолт 0 | `mround(get_held_up_money())` | сколько спишется ближайшим списанием (удержанные деньги) |
  | `full_period_cost_rub_cents` | `int`, дефолт 0 | `get_debt_info(include_prepay=True)[2]` | полная стоимость текущего периода с предоплатой; зависит от `was_fully_payed` и баланса |
  | `full_planned_cost_rub_cents` | `int`, дефолт 0 | `unit_price × periods_planned` | stand-alone цена запланированного периода для модалок «Подтвердите запуск» / «Остановка». Мультипликатор ровно один: `periods_planned` (ЮЛ/ИП 1, физлицо весь срок), на `term_months` НЕ домножать |
  | `discount_percent` | `int`, дефолт 0 | поле модели | снимок скидки ЭТОГО акта; единственный источник процента для акта (не `CloudServer.term_discount_percent` и не глобальный справочник) |
  | `promocode_code` | `Optional[str]` | `get_promocode_code` | код применённого промокода или `None` |
  | `promocode_discount_value` | `Optional[int]` | `get_promocode_discount_value` | процент, только для процентного промокода; для фиксированного (в рублях) `None` при заполненном `promocode_code` |

- **Холодное хранение в `CloudServer` (DSD-013 / DSD-024, уже на `develop`).** 8 read-only полей `UserConfigurationSerializer`, у работающего сервера все `None`:

  | Поле | Тип | Источник на сервере | Смысл |
  |---|---|---|---|
  | `cold_storage_since` | `Optional[str]` (ISO) | поле модели | когда ВМ ушла в холодное хранение |
  | `cold_storage_planned_at` | `Optional[str]` (ISO) | `get_cold_storage_planned_at` | оценка, когда ВМ уедет в хранение (никогда в прошлом); `None` = не планируется |
  | `days_idle` | `Optional[int]` | `get_days_idle` | полных суток простоя остановленной ВМ; `None` у работающей. `0` это значение, не «нет данных» |
  | `cold_grace_deadline` | `Optional[str]` (ISO) | `get_cold_grace_deadline` | дедлайн удаления тома, только в `ServerState.COLD_GRACE` |
  | `cold_storage` | `Optional[ColdStorage]` | `get_cold_storage` | `{act_id, started_at, storage_gb (str), monthly_price_rub_cents, accrued_debt_rub_cents, billed_until_dt}`; только в `COLD_STORAGE_STATES` (1000/1100) и только при открытом акте, иначе `None` |
  | `cold_free` | `Optional[ColdFreeWindow]` | `get_cold_free` | `{free_until_dt, storage_gb (str или null), hour_price_rub_cents, month_price_rub_cents}`: бесплатное окно хранения диска остановленной ВМ. `free_until_dt` может быть в прошлом (окно кончилось, почасовой прогон ещё не дошёл) |
  | `resume_usage_act` | `Optional[UsageAct]` | `get_resume_usage_act` | во что обойдётся возобновление холодной ВМ (`UsageActShortSerializer`, та же модель, что `usage_act`); у холодной ВМ `usage_act` при этом `None`, mock-акт для неё не строится |
  | `migration_error` | `Optional[str]` | поле модели | текст последней ошибки миграции после исчерпанных автопопыток (NoValidHost); причина зависшего IDLE |

  `storage_gb` в обоих блоках приходит СТРОКОЙ (`Decimal(10,3)`), в клиенте так и остаётся: объём только показывается, во float не переводить. `cold_free` и `cold_storage` взаимоисключающие блоки «до» и «после» одной формы. Цены и долг считает бэк, в клиенте их не пересчитывать.
- **Срок аренды в `CloudServer` (реформа тарифов, MIAN-414/415, серверная ветка `feature/pricing-plans-revision`).** 17 read-only полей `UserConfigurationSerializer`, все на модели `CloudServer` с нейтральными дефолтами для старого сервера (`0` / `None` / `False` / `""`):

  | Поле | Тип | Источник на сервере | Смысл |
  |---|---|---|---|
  | `term_months` | `int`, дефолт 0 | поле модели | снимок обязательства в месяцах; 0 = обязательства нет |
  | `term_discount_percent` | `int`, дефолт 0 | поле модели | снимок скидки за срок, целые проценты; правка справочника цен его не меняет |
  | `term_started_at` | `Optional[str]` (ISO) | поле модели | начало срока, `None` до первого акта |
  | `term_ends_at` | `Optional[str]` (ISO) | `get_term_ends_at` → `term_ends_at_effective()` | конец срока С УЧЁТОМ простоя по нашей вине, включая ещё не закрытый |
  | `term_conditions_accepted_at` | `Optional[str]` (ISO) | поле модели | когда клиент принял условие о пересчёте при досрочном прекращении; не обнуляется после срока |
  | `term_renewal_accepted_at` | `Optional[str]` (ISO) | поле модели | клиент нажал «продлить на тех же условиях»; новый срок стартует по истечении текущего |
  | `term_outage_shift_hours` | `int`, дефолт 0 | property (`term_outage_shift_seconds // 3600`) | учтённый сдвиг конца срока за наш простой, часы вниз |
  | `term_outage_active` | `bool` | property | прямо сейчас сервер лежит по нашей вине, конец срока уезжает |
  | `term_state` | `str`, дефолт `""` | property | код из `TermState`; `""` = только старый сервер, который поле не шлёт; у срочного тарифа без снимка приходит `no_snapshot`. Неизвестный код НЕ подменять |
  | `has_term_snapshot` | `bool` | property | снимок применим к текущему `price_plan` |
  | `is_renewal_mandatory` | `bool` | property | срок идёт и подтверждён: платежи внутри срока спишутся независимо от тумблера, выход только «прекратить аренду». Выключить тумблер можно (не продлевать после конца срока), включить через API v2 нельзя (409 `AUTO_RENEWAL_CONSENT_REQUIRED`) |
  | `is_bound_by_term` | `bool` | property | досрочное прекращение = пересчёт без скидки (включает `pending_consent`) |
  | `requires_term_consent` | `bool` | `get_requires_term_consent` | перед запуском нужно собрать согласие; правило живёт на сервере, фронт/SDK его НЕ выводят из `price_plan` |
  | `term_renewal_available` | `bool` | `get_term_renewal_available` | окно продления открыто, срок подтверждён, продление ещё не принято |
  | `term_renewal_pending` | `bool` | property | продление принято и ждёт конца текущего срока |
  | `billing_cycle_months` | `int`, дефолт 0 | property | сколько месяцев списывается за раз. Срочный тариф: ЮЛ/ИП 1, физлицо весь срок; почасовой 1; постоплата `abs(price_plan)`. Читать вместе с `server_full_rent_price_rub_cents` |
  | `pays_term_monthly` | `bool`, дефолт `False` | property | владелец платит срок помесячно (`True`, ЮЛ/ИП с реквизитами) или внёс всю сумму вперёд (`False`, физлицо и ЮЛ/ИП без реквизитов). Внутри срока это СНИМОК типа клиента на дату согласия (`term_client_kind`, оферта п. 8.5), а не живой `legal`: ЮЛ, дозаполнившее ИНН внутри срока, условия не меняет. Снимка нет → сервер читает живой `ICUser.is_term_business`. Парный к `billing_cycle_months`: `True` ↔ 1, `False` ↔ весь срок |

  Флаги `is_*` / `*_pending` / `*_available` и `term_state` это готовый ответ сервера, в клиенте их из дат не пересчитывать: на сервере эти правила уже трижды разъезжались, когда их считали в двух местах.
- **`User.is_term_business`** (`UserSerializer`, та же серверная ветка; `bool`, дефолт `False`). Бизнес-клиент для срочного тарифа по оферте п. 8.5: `legal` в `org`/`ip` **И** заполнены `company_name`, `inn`, `ogrn` (у ИП ОГРНИП). Одного `legal` мало: ЮЛ без ИНН считается физлицом, платит весь срок вперёд, и доплату с него не взыскать. Это ЖИВОЙ предикат по текущему профилю: он говорит, как будет оплачен НОВЫЙ срок; про идущий срок отвечает снимок `CloudServer.pays_term_monthly`. В клиенте не выводить из `legal` / `company_name` (`inn` и `ogrn` в API v2 вообще не отдаются): правило живёт на сервере, второй копии не заводить. Тесты: `TestIsTermBusiness` в `tests/test_term_fields.py`.
- **Автопродление под сроком (`update(is_auto_renewal=...)`, гард `assert_auto_renewal_change_allowed` в `services/term_obligation.py`).** Выключить (`False`) можно всегда: отказ от продления в любой момент (решение владельца 17.09.2026; прежний 400 `validate_is_auto_renewal` удалён). Включить (`True`) под идущим подтверждённым сроком (`is_renewal_mandatory`) нельзя через API v2 вовсе: **409 `AUTO_RENEWAL_CONSENT_REQUIRED`**, включение продлевает срок, включает только сам клиент переключателем на карточке в ЛК (окна и документа с 29.09.2026 нет). Под `term_state == "pending_consent"` (тумблер выбран в подписанном документе) и на истёкшем подтверждённом сроке, который ещё не остановлен: **409 `AUTO_RENEWAL_NOT_APPLICABLE`**. Вне срока всё как раньше. Тело `{error_code, message, detail}`, код читать через `APIError.error_code` и сравнивать с `TermConflictCode`, не с текстом.
- **`start(id, is_auto_renewal=...)` под сроком** (`is_bound_by_term`, гард `apply_auto_renewal_on_start`): параметр **игнорируется** молча, ответ 200, тумблер остаётся таким, как в подписанном документе (иначе дефолт вьюхи включал бы продление физлицу, подписавшему «выключено»). Менять тумблер только через `update()`. В окне перезавода срока старт отдаёт **409 `TERM_RENEWAL_IN_PROGRESS`** (повтор через минуту не гарантирован, причину называет текст сервера). Тесты: `tests/test_auto_renewal_term.py`.
- **Согласие на условия, продление и досрочное прекращение живут под `lk/cloud-servers/<id>/...` (session-only, вне схемы API v2), в SDK их методов нет и не должно быть, пока сервер не вынесет их в `/api/v2/`.
- **`ServerStatus` (`GET cloud-servers/{id}/status/`, вьюха `retrieve_server_can_start`, та же серверная ветка).** Помимо `can_start` и `affordable_runtime_seconds` клиент читает `is_enough_money_for_full_period` (`Optional[bool]`, сервер шлёт 0/1), `remaining_monthly_seconds` (`Optional[int]`) и новые `launch_required_rub_cents` (`Optional[int]`, копейки): сколько свободных денег нужно прямо сейчас, чтобы запуск состоялся, и `launch_funds_rub_cents` (`Optional[int]`, копейки): деньги клиента, с которыми гейт это сравнит (`UserConfiguration.payment_funds_rub_cents`). У физлица на срочном тарифе это только свои деньги без лимита овердрафта (п. 8.5 Условий), поэтому бывает отрицательным; у ЮЛ/ИП на сроке и вне срока свободный баланс с лимитом. Сравнивать два поля как пришли, сумму из профиля не пересобирать. Единственная серверная формула (`services/configuration.launch_required_funds_rub_cents`): остаток идущего цикла, весь следующий акт, либо `0`, когда открытый акт уже покрывает запуск (сервер, выключенный под подтверждённым сроком). Оба `None` при `can_start=False`: сервер тогда числа не считает, а `0` читался бы как «запуск бесплатен». Первые два поля сервер отдавал и раньше, клиент их молча выбрасывал (та же болезнь, что у PR #526). Тесты: `tests/test_status_and_reject_reason.py`.
- **Сверка с сериализаторами (PRT-86, 23.10.2026).** Состав полей `UserConfigurationSerializer`, `FlavorConfigSerializer`, GPU/CPU/RAM/SSD, `OperationalSystemImageSerializer`, `UserSerializer`, `UsageActShortSerializer`, `UserConfigurationAddonSerializer` сверен с моделями по коду сериализаторов (не по OpenAPI). Нашлось и добавлено: поля `User` (`overdraft_limit_rub_cents`, `held_up_money_rub`, `bonus_balance_rub_cents`, `is_kyc_needed`, `has_max`, `is_beta_tester`, `is_access_to_aiapi_granted`, `date_joined`, `cold_storage_summary`), `CloudServer.disk_extend_order`, `ColdFreeWindow.free_hours`, `SoftwareAddonInstance.slug` и `last_install_log*` (лог сервер заполняет только при `status == "failed"`), аргументы `create(ssh_key_ids=)` и `migrate(ssd_count=)`. Остаток: `User.invalid_name` есть в клиенте, `UserSerializer` его не отдаёт (всегда `False`, оставлено ради совместимости). Не покрыты ресурсами SDK (поля сверялись только у существующих моделей): `UsageActSerializer` (вложен в `events/`), `events/`, `alerts/`, `exchange-rates/`, `dedicated-servers/`, `extend-disk/*`, `vnc-console/`, `metrics/`, `termination-quote/`. Тесты: `tests/test_serializer_sweep_fields.py`. Следующую сверку делать так же: `ast` по `Meta.fields` против `dataclasses.fields`, затем руками методы-поля.
- **`APIError.reason` и `ServerCreateRejectReason`.** `POST cloud-servers/` кладёт в свои 400/409 тела машинный ярлык `reason` рядом с `detail` (MIAN-412; `cpu_limit` в 400, `queue_disabled` в 409, `validation`/`internal_error` только в серверный лог). Читать через свойство `APIError.reason` (`Optional[str]`, `None` если ключа нет, в том числе у DRF-ошибок валидации с `field_errors`), сравнивать с константами `ServerCreateRejectReason`, а не с русским `detail`: текст меняется при первой правке копирайта.
- **⚠️ OpenAPI-схема врёт про типы этих полей.** drf-spectacular типизирует любой `SerializerMethodField` как `string`, поэтому в `/api/schema/` `queue_disabled` числится строкой, а `suggested_alternative` и `password_rotation` — тоже строками. Реально это `bool` и два вложенных объекта. Из полей срока под ту же ловушку попадают `term_ends_at` (реально nullable datetime), `requires_term_consent` и `term_renewal_available` (реально `bool`). `pays_term_monthly` и `User.is_term_business` объявлены `BooleanField(read_only=True)`, в схеме они честные `boolean`. Из полей холодного хранения: `cold_storage_planned_at`, `cold_grace_deadline` (nullable datetime), `days_idle` (nullable int), `cold_storage`, `cold_free`, `resume_usage_act` (nullable объекты). Из полей `UsageAct`: `next_charge_rub_cents`, `full_period_cost_rub_cents`, `full_planned_cost_rub_cents` (реально `int`), `promocode_code`, `promocode_discount_value` (реально nullable str / int). Сверять с сериализаторами (`website/servers/serializers.py`, `website/user_panel/serializers.py`), а не со схемой.

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

> [!danger] Release-gating: не релизить раньше сервера
> Артефакт на PyPI **иммутабелен** — версию нельзя удалить или перезалить. Поэтому НЕЛЬЗЯ выпускать версию, которая объявляет поля/эндпоинты из серверного PR, ещё **не влитого в прод**: SDK начнёт обещать то, чего сервер не отдаёт, и это не откатить.
>
> **Порядок строгий:** сначала мерж серверного PR в `develop`/прод → потом тег и релиз клиента. Если код клиента готов раньше — держи его в ветке/PR библиотеки, но тег не ставь.
>
> Пример (2026-07): клиент v0.4.0 (`queue_disabled`, `suggested_alternative`) готов и оттестирован, но его поля приходят из `client_board` PR #526, который на тот момент открыт → релиз отложен, код лежит в ветке `feature/queue-disabled-fields`.

> [!warning] Права на репозиторий: релиз не у всех
> У аккаунта `JamesonDeagle` push-доступ к `client_board` есть, но к `IntelionCloud/ic_python_client` — **только чтение** (`gh api repos/IntelionCloud/ic_python_client --jq .permissions` → `push:false`). Ни ветку, ни тег запушить нельзя (403). Если работаешь под этим аккаунтом, готовь передачу тому, у кого есть write:
> - **Код** (новые коммиты) → `git bundle create out.bundle origin/main..<ветка>` + инструкция (получатель: `git fetch out.bundle <ветка>:<ветка>` → push → PR). Запасной способ — `git format-patch` + `git am`.
> - **Релиз уже влитого кода** → человек с доступом ставит тег `vX.Y.Z` на `main` (через GitHub UI: Releases → Draft, или `git push origin vX.Y.Z`). Код передавать не нужно, если он уже в `main`.

**По SemVer:**
- `MAJOR` (0.x → 1.0, 1.x → 2.0) — ломающие изменения публичного API клиента. Любое изменение сигнатуры публичного метода, переименование/удаление поля модели, изменение endpoint/payload — это breaking для потребителя SDK.
- `MINOR` (0.2 → 0.3) — новые ресурсы/методы/поля без ломки существующих.
- `PATCH` (0.2.0 → 0.2.1) — багфиксы, обновление README/docs (PyPI-описание обновляется только при новой версии — артефакты на PyPI иммутабельны).

### Как выпустить новую версию

0. **Пре-флайт (проверить ДО тега):**
   - Серверный PR, поля которого объявляет эта версия, **влит в прод**? Если нет — стоп (см. release-gating выше).
   - Тесты зелёные в Docker (`docker build -t ic_client_test . && docker run --rm ic_client_test pytest tests/ -q`).
   - В `CHANGELOG.md` есть секция этой версии (заводится вместе с правкой, а не в день релиза; GitHub Release добавляет к ней только список коммитов), `(unreleased)` в заголовке заменить датой.
   - Есть write-доступ к репозиторию? Если только чтение — не пытаться пушить, готовить передачу (см. блок про права выше).

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
   - Соберёт `sdist + wheel`.
   - Проверит `twine check`.
   - Зальёт на PyPI через OIDC (job `publish`, environment `pypi`).
   - Создаст GitHub Release с авто-сгенерированным changelog'ом и приложит артефакты.

   **Тесты в release.yml НЕ гоняются** (убрано 2026-09-02, self-hosted раннер
   в моменте лежал) — релиз полагается на то, что тег ставится на коммит, где
   `pytest` уже зелёный (см. шаг 1 выше). Полная матрица (3.9–3.13) всё равно
   гоняется отдельно в `test.yml` на каждый push/PR в `main`, до тега.

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

Отдельный workflow `test.yml` прогоняет pytest на матрице Python 3.9–3.13 на
каждый push в `main` и каждый PR. **С 2026-09-02 релизный `release.yml` тесты
САМ больше не гоняет** (см. Release process выше) — если тесты красные, это
уже не остановит релиз автоматически, ловить нужно до тега, глазами на
`test.yml`.

**⚠️ `test.yml` всё ещё `runs-on: self-hosted`** (в отличие от `release.yml`,
переведённого на `ubuntu-latest` 2026-09-02 после того, как self-hosted раннер
лёг и держал весь релизный пайплайн — не только тесты — сутки). Тот же риск
здесь не устранён: если раннер снова ляжет, `test.yml` будет тихо висеть
`queued` на каждый push/PR в `main`, и это не заметят, пока кому-то не
понадобится зелёная галочка. Матрице 3.9–3.13 self-hosted тоже не нужен (то
же самое рассуждение, что для `release.yml` — тесты не трогают внутреннюю
сеть), но сознательно не тронуто в этом заходе — не было отдельного запроса,
трогать чужой рабочий workflow без причины не стала. Если увидишь, что PR
висит без CI-результата дольше пары минут — сначала проверь
https://github.com/IntelionCloud/ic_python_client/actions, не жди.
