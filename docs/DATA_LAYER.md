# Слой данных (Data Layer)

Слой данных отвечает за хранение, шифрование и управление пользовательскими данными.

---

## Структура модулей

```
src/data/
├── storage.py     # Хранилище данных (SQLite + кеширование)
├── encryption.py  # Шифрование и дешифрование
└── models.py      # Структуры данных (TypedDict, dataclasses)
```

---

## 1. storage.py - Хранилище данных

### Архитектура базы данных

**SQLite Database:** `user_data/mood_tracker.db`

#### Таблица: users

```sql
CREATE TABLE users (
    chat_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    notification_time TEXT
);
```

**Поля:**
- `chat_id` - Telegram ID пользователя (PRIMARY KEY)
- `username` - username в Telegram
- `first_name` - имя пользователя
- `notification_time` - время уведомления в формате HH:MM (UTC) или NULL

#### Таблица: entries

```sql
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    encrypted_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_id) REFERENCES users(chat_id),
    UNIQUE(chat_id, date)
);
```

**Поля:**
- `id` - автоинкремент ID
- `chat_id` - ID пользователя (FOREIGN KEY)
- `date` - дата записи (YYYY-MM-DD)
- `encrypted_data` - зашифрованные данные (base64)
- `created_at` - timestamp создания

**Ограничения:**
- `UNIQUE(chat_id, date)` - одна запись на дату
- `FOREIGN KEY` - каскадное удаление при удалении пользователя

#### Индексы

```sql
-- Оптимизация поиска по пользователю
CREATE INDEX idx_entries_chat_id ON entries(chat_id);

-- Оптимизация поиска по дате
CREATE INDEX idx_entries_date ON entries(date);

-- Оптимизация запроса уведомлений (выполняется каждые 60 секунд)
CREATE INDEX idx_users_notification_time
ON users(notification_time)
WHERE notification_time IS NOT NULL;
```

### Кеширование

#### Структура кеша

```python
_entries_cache: Dict[int, Dict[str, Any]] = {}

# Структура элемента кеша:
{
    chat_id: {
        "data": List[Dict],      # Расшифрованные записи
        "timestamp": datetime,   # Время последнего обращения
        "modified": bool         # Флаг изменений
    }
}
```

#### Параметры кеша

```python
MAX_CACHE_SIZE = 5           # Максимум пользователей в кеше
CACHE_TTL = 1800             # TTL 30 минут (секунды)
```

#### Логика кеширования

**При чтении данных:**
1. Проверка наличия в кеше
2. Проверка актуальности (TTL)
3. Если актуально - возврат из кеша
4. Если нет - загрузка из БД и кеширование

**При записи данных:**
1. Сохранение в кеш с флагом `modified=True`
2. Если размер кеша > MAX_CACHE_SIZE - сброс в БД
3. Фоновая синхронизация каждые N операций

**При очистке:**
1. Проверка TTL для всех записей
2. Сброс модифицированных записей в БД
3. Удаление устаревших из кеша

### Основные функции

#### save_data()
```python
def save_data(data: Dict[str, Any], chat_id: int) -> bool
```

**Назначение:** Сохранение записи дневника

**Процесс:**
1. Обновление/добавление в кеш
2. Пометка как modified
3. Обеспечение наличия пользователя в БД
4. Немедленный сброс в БД (для важных данных)

**Шифрование:** Автоматическое через `encrypt_data()`

#### get_user_entries()
```python
def get_user_entries(
    chat_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]
```

**Назначение:** Получение расшифрованных записей пользователя

**Параметры:**
- `chat_id` - ID пользователя
- `start_date` - начальная дата фильтрации (опционально)
- `end_date` - конечная дата фильтрации (опционально)

**Возврат:** Список расшифрованных записей, отсортированных по дате (DESC)

**Процесс:**
1. Проверка кеша (если без фильтров)
2. Запрос из БД
3. Расшифровка каждой записи
4. Обновление кеша (если без фильтров)

#### save_user()
```python
def save_user(
    chat_id: int,
    username: Optional[str],
    first_name: Optional[str],
    notification_time: Optional[str] = None
) -> bool
```

**Назначение:** Сохранение/обновление информации о пользователе

**ВАЖНО:** При `notification_time=None` поле устанавливается в NULL (отключение уведомлений)

**Процесс:**
1. Проверка существования пользователя
2. INSERT (если новый) или UPDATE (если существует)
3. Всегда обновляет notification_time (даже при None)

#### get_users_for_notification()
```python
def get_users_for_notification(current_time: str) -> List[Dict[str, Any]]
```

**Назначение:** Получение пользователей для отправки уведомлений

**SQL:**
```sql
SELECT chat_id, username, first_name, notification_time
FROM users
WHERE notification_time = ?
```

**Оптимизация:** Использует индекс `idx_users_notification_time`

#### has_entry_for_date()
```python
def has_entry_for_date(chat_id: int, date: str) -> bool
```

**Назначение:** Проверка наличия записи за дату

**Процесс:**
1. Проверка в кеше (если есть)
2. Запрос в БД (если нет в кеше)

**SQL:**
```sql
SELECT 1 FROM entries
WHERE chat_id = ? AND date = ?
LIMIT 1
```

#### delete_all_entries()
```python
def delete_all_entries(chat_id: int) -> bool
```

**Назначение:** Удаление всех записей пользователя

**Процесс:**
1. Очистка кеша пользователя
2. Удаление из БД

#### delete_entry_by_date()
```python
def delete_entry_by_date(chat_id: int, date: str) -> bool
```

**Назначение:** Удаление записи за конкретную дату

**Процесс:**
1. Удаление из кеша (если есть)
2. Удаление из БД

### Миграция из CSV

#### _migrate_csv_to_sqlite()
```python
def _migrate_csv_to_sqlite() -> None
```

**Назначение:** Автоматическая миграция старых CSV-файлов в SQLite

**Процесс:**
1. Поиск файлов `user_*_data.csv` в DATA_FOLDER
2. Извлечение chat_id из имени файла
3. Проверка, не мигрирован ли уже
4. Чтение CSV через pandas
5. Вставка записей в SQLite
6. Создание резервной копии CSV (*.csv.bak)

**Запуск:** Автоматически при `initialize_storage()`

### Thread Safety

**Механизмы:**
```python
_cache_lock = threading.RLock()  # Для кеша
_db_lock = threading.RLock()      # Для БД

with _cache_lock:
    # Операции с кешем

with _db_lock:
    # Операции с БД
```

**Важно:** RLock (reentrant lock) позволяет повторный захват тем же потоком

---

## 2. encryption.py - Шифрование

### Криптографический стек

**Библиотека:** cryptography (Python)
**Алгоритм:** Fernet (симметричное шифрование)
**Основа:** AES-128 в режиме CBC
**MAC:** HMAC с SHA256

### KDF (Key Derivation Function)

**Алгоритм:** PBKDF2
**Hash:** SHA256
**Итерации:**
- 25000 для личных данных
- 10000 для обмена (баланс скорость/безопасность)
**Соль:** SYSTEM_SALT (32 байта) + SECRET_SALT (из config)

#### generate_user_key()
```python
def generate_user_key(chat_id: int) -> bytes
```

**Назначение:** Генерация уникального ключа для пользователя

**Процесс:**
```python
salt = SYSTEM_SALT + SECRET_SALT + str(chat_id).encode()
key = PBKDF2(
    password=str(chat_id),
    salt=salt,
    iterations=25000,
    dkLen=32,
    hmac_hash_module=SHA256
)
fernet_key = base64.urlsafe_b64encode(key)
```

**Кеширование:**
```python
_key_cache: Dict[int, Dict[str, Any]] = {}

{
    chat_id: {
        "key": bytes,
        "timestamp": datetime
    }
}

KEY_CACHE_TTL = 3600  # 1 час
```

**Преимущества кеширования:**
- PBKDF2 - дорогостоящая операция (25000 итераций)
- Ключ не изменяется для пользователя
- Значительное ускорение операций

### Шифрование данных

#### encrypt_data()
```python
def encrypt_data(data: Dict[str, Any], chat_id: int) -> str
```

**Назначение:** Шифрование записи дневника

**Процесс:**
1. Получение/генерация ключа пользователя
2. Сериализация данных в JSON
3. Шифрование через Fernet
4. Кодирование в base64
5. Возврат как строка

**Сериализация:**
- Поддержка datetime объектов
- Поддержка pandas Timestamp
- Поддержка вложенных структур

#### decrypt_data()
```python
def decrypt_data(encrypted_data: str, chat_id: int) -> Optional[Dict[str, Any]]
```

**Назначение:** Расшифровка записи дневника

**Процесс:**
1. Получение ключа пользователя
2. Декодирование из base64
3. Расшифровка через Fernet
4. Десериализация JSON

**Обработка ошибок:**
- Невалидный токен → None
- Неверный ключ → None
- Поврежденные данные → None
- Логирование всех ошибок

### Обмен данными

#### encrypt_for_sharing()
```python
def encrypt_for_sharing(data: Any, password: str) -> str
```

**Назначение:** Облегченное шифрование для отправки другим пользователям

**Отличия от личного шифрования:**
- Использует PBKDF2 с 10000 итераций (вместо 25000)
- Генерирует случайную соль для каждой отправки
- Ключ основан на пароле, а не chat_id
- Оптимизировано для скорости

**Процесс:**
```python
salt = secrets.token_bytes(32)
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=10000
)
key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
encrypted = Fernet(key).encrypt(json_data)
return base64.b64encode(salt + encrypted).decode()
```

**Формат:** `base64(salt + encrypted_data)`

#### decrypt_shared_data()
```python
def decrypt_shared_data(encrypted_data: str, password: str) -> Optional[Any]
```

**Назначение:** Расшифровка полученных данных

**Процесс:**
1. Декодирование base64
2. Извлечение соли (первые 32 байта)
3. Деривация ключа из пароля + соль
4. Расшифровка оставшихся данных
5. Десериализация JSON

### Безопасность

**Strengths:**
- Уникальный ключ для каждого пользователя
- Невозможно расшифровать данные другого пользователя
- PBKDF2 защищает от brute-force
- Fernet обеспечивает аутентификацию (MAC)
- Случайная соль для каждой отправки

**Considerations:**
- Ключи кешируются (компромисс производительность/безопасность)
- SECRET_SALT хранится в конфиге (должен быть в .env)
- Нет ротации ключей (пока)

---

## 3. models.py - Структуры данных

### TypedDict определения

#### UserDict
```python
class UserDict(TypedDict):
    chat_id: int
    username: Optional[str]
    first_name: Optional[str]
    notification_time: Optional[str]
```

**Использование:** Типизация пользовательских данных

#### EntryDict
```python
class EntryDict(TypedDict):
    date: str
    mood: str
    sleep: str
    comment: str
    balance: str
    mania: str
    depression: str
    anxiety: str
    irritability: str
    productivity: str
    sociability: str
```

**Использование:** Типизация записей дневника

**Примечание:** Все поля хранятся как строки для упрощения сериализации

#### SharedPackage
```python
class SharedPackage(TypedDict):
    encrypted_data: str
    sender_id: int
    format_version: str
```

**Использование:** Формат пакета для обмена данными

### Dataclass модели

#### Entry
```python
@dataclass
class Entry:
    date: str
    mood: int
    sleep: int
    comment: str
    balance: int
    mania: int
    depression: int
    anxiety: int
    irritability: int
    productivity: int
    sociability: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entry':
        """Создание из словаря"""

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
```

**Использование:** Работа с записями как объектами

#### User
```python
@dataclass
class User:
    chat_id: int
    username: Optional[str]
    first_name: Optional[str]
    notification_time: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Создание из словаря"""

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
```

**Использование:** Работа с пользователями как объектами

### Преобразования типов

**Словарь → Объект:**
```python
entry_obj = Entry.from_dict(entry_dict)
```

**Объект → Словарь:**
```python
entry_dict = entry_obj.to_dict()
```

---

## Потоки данных

### Сохранение записи

```
Handler (entry.py)
    ↓
save_data(data, chat_id)
    ↓
_entries_cache[chat_id] = {"data": [data], "modified": True}
    ↓
encrypt_data(data, chat_id)
    ↓
generate_user_key(chat_id) → [Кеш ключей]
    ↓
Fernet.encrypt(json_data)
    ↓
base64.encode()
    ↓
INSERT INTO entries (chat_id, date, encrypted_data)
```

### Чтение записей

```
Handler (stats.py)
    ↓
get_user_entries(chat_id)
    ↓
Проверка _entries_cache[chat_id]
    ↓ (если нет)
SELECT date, encrypted_data FROM entries WHERE chat_id = ?
    ↓
decrypt_data(encrypted_data, chat_id)
    ↓
generate_user_key(chat_id) → [Кеш ключей]
    ↓
Fernet.decrypt(encrypted_data)
    ↓
json.loads()
    ↓
List[Dict] → Handler
```

### Обмен данными

```
Handler (sharing.py)
    ↓
get_user_entries(chat_id) → List[Dict]
    ↓
Фильтрация по датам (pandas)
    ↓
encrypt_for_sharing(filtered_data, password)
    ↓
Генерация соли (32 байта)
    ↓
PBKDF2(password, salt, 10000 итераций)
    ↓
Fernet.encrypt(json_data)
    ↓
base64.encode(salt + encrypted)
    ↓
JSON packaging: {"encrypted_data": ..., "sender_id": ..., "format_version": ...}
    ↓
Send as document → Получатель
```

---

_Конец документации слоя данных_
