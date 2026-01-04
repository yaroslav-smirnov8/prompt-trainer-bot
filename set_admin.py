import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from database.models import Base
from database.crud import set_admin_status, get_user

# Конфигурация базы данных
DATABASE_URL = "sqlite+aiosqlite:///./trainbot.db"

# Создание асинхронного движка и сессии
async_engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def set_admin(user_id: int, is_admin: bool = True):
    """Установить статус администратора для пользователя"""
    async with AsyncSessionLocal() as session:
        user = await get_user(session, user_id)
        if not user:
            print(f"Пользователь с ID {user_id} не найден")
            return False
        
        await set_admin_status(session, user_id, is_admin)
        print(f"Пользователь {user.username or user.user_id} {'теперь администратор' if is_admin else 'больше не администратор'}")
        return True


async def main():
    if len(sys.argv) < 2:
        print("Использование: python set_admin.py <user_id1> [user_id2 ...] [--remove]")
        return
    
    # Проверяем наличие флага --remove
    is_admin = "--remove" not in sys.argv
    user_ids = [int(arg) for arg in sys.argv[1:] if arg != "--remove" and arg.isdigit()]
    
    if not user_ids:
        print("Не указаны ID пользователей")
        return
    
    for user_id in user_ids:
        await set_admin(user_id, is_admin)


if __name__ == "__main__":
    # Запускаем асинхронную функцию main
    asyncio.run(main())
