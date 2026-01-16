import asyncio
from typing import Callable, Dict, Any, Awaitable, Optional
from loguru import logger
import sys

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import config as settings
from bot.handlers import basic, text_lessons, image_lessons, quiz, generation, admin
from database import crud
from database.models import Base
from database.populate import populate_text_lessons, populate_image_lessons, populate_quizzes


# ===== USER ID EXTRACTION UTILITY =====

class UserIdExtractor:
    """Centralized utility for extracting user_id from various Telegram event types."""
    
    # Define extraction strategies as a list of (attribute_path, accessor) tuples
    EXTRACTION_STRATEGIES = [
        (('from_user',), lambda obj: obj.id),
        (('chat',), lambda obj: obj.id),
        (('message', 'from_user'), lambda obj: obj.id),
        (('callback_query', 'from_user'), lambda obj: obj.id),
        (('edited_message', 'from_user'), lambda obj: obj.id),
        (('channel_post', 'chat'), lambda obj: obj.id),
        (('edited_channel_post', 'chat'), lambda obj: obj.id),
        (('inline_query', 'from_user'), lambda obj: obj.id),
        (('chosen_inline_result', 'from_user'), lambda obj: obj.id),
        (('shipping_query', 'from_user'), lambda obj: obj.id),
        (('pre_checkout_query', 'from_user'), lambda obj: obj.id),
        (('poll_answer',), lambda obj: obj.user.id if obj.user else None),
        (('my_chat_member', 'from_user'), lambda obj: obj.id),
        (('chat_member', 'from_user'), lambda obj: obj.id),
        (('chat_join_request', 'from_user'), lambda obj: obj.id),
    ]

    @classmethod
    def extract_user_id(cls, event: TelegramObject) -> Optional[int]:
        """
        Extract user_id from a Telegram event using configured strategies.
        
        Args:
            event: Telegram event object
            
        Returns:
            user_id if found, None otherwise
        """
        for attr_path, accessor in cls.EXTRACTION_STRATEGIES:
            try:
                obj = event
                # Navigate through attribute path
                for attr in attr_path:
                    if not hasattr(obj, attr):
                        break
                    obj = getattr(obj, attr)
                    if obj is None:
                        break
                else:
                    # All attributes in path exist and are not None
                    user_id = accessor(obj)
                    if user_id is not None:
                        return user_id
            except (AttributeError, TypeError):
                continue
        
        return None


async def ensure_admin_users(session: async_sessionmaker):
    """Ensures that users specified in ADMIN_ID environment variable are set as admins."""
    admin_ids_str = str(settings.bot.admin_id)
    if not admin_ids_str or admin_ids_str == "0":
        logger.info("No ADMIN_ID specified in .env, skipping admin setup.")
        return

    admin_ids = [int(uid.strip()) for uid in admin_ids_str.split(',') if uid.strip().isdigit()]

    if not admin_ids:
        logger.warning(f"Invalid ADMIN_ID format: {admin_ids_str}. Please use comma-separated integers.")    
        return

    logger.info(f"Ensuring admin status for IDs: {admin_ids}")

    for user_id in admin_ids:
        try:
            user = await crud.get_user_safe(session, user_id)
            if user:
                if not user.is_admin:
                    await crud.set_admin_status(session, user_id, is_admin=True)
                    logger.info(f"User {user_id} (username: {user.username}) successfully set as admin.")    
                else:
                    logger.info(f"User {user_id} (username: {user.username}) is already an admin.")
            else:
                logger.warning(f"User with Telegram ID {user_id} not found in database. Cannot set as admin. Please ask them to start the bot first.")
        except Exception as e:
            logger.error(f"Error setting admin status for user {user_id}: {e}")


class SessionMiddleware(BaseMiddleware):
    def __init__(self, sessionmaker: async_sessionmaker):
        self.sessionmaker = sessionmaker

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = UserIdExtractor.extract_user_id(event)
        event_type = type(event).__name__
        logger.info(f"SessionMiddleware: Processing event type={event_type}, user_id={user_id}")
            
        async with self.sessionmaker() as session:
            data["session"] = session
            logger.info(f"SessionMiddleware: Created session for user_id={user_id}, event_type={event_type}")
            
            try:
                result = await handler(event, data)
                await session.commit()
                logger.info(f"SessionMiddleware: Successfully processed event for user_id={user_id}")
                return result
            except Exception as e:
                await session.rollback()
                logger.error(f"SessionMiddleware: Error processing event for user_id={user_id}: {e}", exc_info=True)
                raise


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = UserIdExtractor.extract_user_id(event)
        
        if user_id is None:
            logger.warning(f"AccessMiddleware: Could not determine user_id for event type={type(event).__name__}. Skipping access check.")
            return await handler(event, data)

        session = data["session"]
        user = await crud.get_user_safe(session, user_id)

        if user and not user.is_active:
            logger.warning(f"AccessMiddleware: User {user_id} is not active. Denying access.")
            
            if isinstance(event, Message):
                await event.answer("Your access to the bot is restricted.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Your access to the bot is restricted.", show_alert=True)
            return

        return await handler(event, data)


class ErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = UserIdExtractor.extract_user_id(event)
        event_type = type(event).__name__
        
        logger.info(f"ErrorHandlingMiddleware: Processing event type={event_type}, user_id={user_id}")
        
        try:
            result = await handler(event, data)
            logger.info(f"ErrorHandlingMiddleware: Successfully processed event for user_id={user_id}")
            return result
        except ValueError as e:
            error_msg = str(e)
            if "User with Telegram ID" in error_msg and "not found" in error_msg:
                logger.error(f"ErrorHandlingMiddleware: User not found error: {error_msg}, user_id={user_id}, event_type={event_type}")
                
                import re
                id_match = re.search(r"User with Telegram ID (\d+) not found", error_msg)
                if id_match:
                    missing_id = id_match.group(1)
                    logger.error(f"ErrorHandlingMiddleware: Missing user with telegram_id={missing_id}")
                    
                    if missing_id == "1":
                        logger.critical(f"ErrorHandlingMiddleware: Detected critical ID 1 error! Event details: {event}")
                        import traceback
                        logger.critical(f"ErrorHandlingMiddleware: Stack trace for ID 1 error:\n{traceback.format_exc()}")
                
                if isinstance(event, Message):
                    await event.reply("An error occurred while processing your request. Please try running the /start command to register in the system.")
                elif isinstance(event, CallbackQuery):
                    await event.answer()
                    await event.message.reply("An error occurred while processing your request. Please try running the /start command to register in the system.")
            else:
                logger.error(f"ErrorHandlingMiddleware: ValueError: {error_msg}, user_id={user_id}", exc_info=True)
                raise
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"ErrorHandlingMiddleware: Unhandled exception: {error_msg}, user_id={user_id}, event_type={event_type}")
            
            if "1" in error_msg and ("ID" in error_msg or "id" in error_msg):
                logger.critical(f"ErrorHandlingMiddleware: Possible ID 1 related error! Error: {error_msg}")
                import traceback
                logger.critical(f"ErrorHandlingMiddleware: Stack trace for possible ID 1 error:\n{traceback.format_exc()}")
            
            if isinstance(event, Message):
                await event.reply("An unexpected error occurred. Please try again later or contact the administrator.")
            elif isinstance(event, CallbackQuery):
                await event.answer()
                await event.message.reply("An unexpected error occurred. Please try again later or contact the administrator.")


async def main():
    # Setup logging
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    # Create engine and session maker
    engine = create_async_engine(settings.db.get_url(), echo=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Populate lessons and quizzes
    async with sessionmaker() as session:
        await populate_text_lessons(session)
        await populate_image_lessons(session)
        await populate_quizzes(session)
        await ensure_admin_users(session)

    # Create bot and dispatcher
    bot = Bot(token=settings.bot.token, parse_mode="HTML")
    dp = Dispatcher()

    # Include routers
    dp.include_router(basic.router)
    dp.include_router(admin.router)
    dp.include_router(text_lessons.router)
    dp.include_router(image_lessons.router)
    dp.include_router(quiz.router)
    dp.include_router(generation.router)

    # Register middlewares
    dp.update.middleware(SessionMiddleware(sessionmaker))
    dp.update.middleware(ErrorHandlingMiddleware())
    dp.update.middleware(AccessMiddleware())

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
