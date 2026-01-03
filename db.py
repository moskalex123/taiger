from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

# DATABASE_URL = "postgresql+asyncpg://taiger:123@94.141.161.21:5432/taigerdb"
# Лучше использовать переменные окружения
DB_USER = os.getenv("DB_USER", "taiger")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Pp969291")  # Fixed default password
DB_HOST = os.getenv("DB_HOST", "94.141.161.21")  # Fixed default host
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "taigerdb")

# Build connection URL with optional password
if DB_PASSWORD:
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SYNC_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SYNC_DATABASE_URL = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True  # Add this line to enable pre-ping
)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Добавлена функция зависимости
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

# Функция для получения сессии БД
async def get_db_session():
    return async_session()

# Функция для получения URL базы данных
def get_database_url():
    return DATABASE_URL

# Функция для получения синхронного URL базы данных
def get_sync_database_url():
    return SYNC_DATABASE_URL