import asyncio
from typing import Callable, Dict, Any, Awaitable
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
        import logging
        user_id = None
        
        # Attempt to get user_id from various event types
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
        elif hasattr(event, 'chat') and event.chat: # For channel posts, etc.
            user_id = event.chat.id
        elif hasattr(event, 'message') and event.message and event.message.from_user:
            user_id = event.message.from_user.id
        elif hasattr(event, 'callback_query') and event.callback_query and event.callback_query.from_user:
            user_id = event.callback_query.from_user.id
        elif hasattr(event, 'edited_message') and event.edited_message and event.edited_message.from_user:
            user_id = event.edited_message.from_user.id
        elif hasattr(event, 'channel_post') and event.channel_post and event.channel_post.chat:
            user_id = event.channel_post.chat.id
        elif hasattr(event, 'edited_channel_post') and event.edited_channel_post and event.edited_channel_post.chat:
            user_id = event.edited_channel_post.chat.id
        elif hasattr(event, 'inline_query') and event.inline_query and event.inline_query.from_user:
            user_id = event.inline_query.from_user.id
        elif hasattr(event, 'chosen_inline_result') and event.chosen_inline_result and event.chosen_inline_result.from_user:
            user_id = event.chosen_inline_result.from_user.id
        elif hasattr(event, 'shipping_query') and event.shipping_query and event.shipping_query.from_user:
            user_id = event.shipping_query.from_user.id
        elif hasattr(event, 'pre_checkout_query') and event.pre_checkout_query and event.pre_checkout_query.from_user:
            user_id = event.pre_checkout_query.from_user.id
        elif hasattr(event, 'poll_answer') and event.poll_answer and event.poll_answer.user:
            user_id = event.poll_answer.user.id
        elif hasattr(event, 'my_chat_member') and event.my_chat_member and event.my_chat_member.from_user:
            user_id = event.my_chat_member.from_user.id
        elif hasattr(event, 'chat_member') and event.chat_member and event.chat_member.from_user:
            user_id = event.chat_member.from_user.id
        elif hasattr(event, 'chat_join_request') and event.chat_join_request and event.chat_join_request.from_user:
            user_id = event.chat_join_request.from_user.id
        
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
        user_id = None
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
        elif hasattr(event, 'chat') and event.chat:
            user_id = event.chat.id
        elif hasattr(event, 'message') and event.message and event.message.from_user:
            user_id = event.message.from_user.id
        elif hasattr(event, 'callback_query') and event.callback_query and event.callback_query.from_user:
            user_id = event.callback_query.from_user.id
        elif hasattr(event, 'edited_message') and event.edited_message and event.edited_message.from_user:
            user_id = event.edited_message.from_user.id
        elif hasattr(event, 'channel_post') and event.channel_post and event.channel_post.chat:
            user_id = event.channel_post.chat.id
        elif hasattr(event, 'edited_channel_post') and event.edited_channel_post and event.edited_channel_post.chat:
            user_id = event.edited_channel_post.chat.id
        elif hasattr(event, 'inline_query') and event.inline_query and event.inline_query.from_user:
            user_id = event.inline_query.from_user.id
        elif hasattr(event, 'chosen_inline_result') and event.chosen_inline_result and event.chosen_inline_result.from_user:
            user_id = event.chosen_inline_result.from_user.id
        elif hasattr(event, 'shipping_query') and event.shipping_query and event.shipping_query.from_user:
            user_id = event.shipping_query.from_user.id
        elif hasattr(event, 'pre_checkout_query') and event.pre_checkout_query and event.pre_checkout_query.from_user:
            user_id = event.pre_checkout_query.from_user.id
        elif hasattr(event, 'poll_answer') and event.poll_answer and event.poll_answer.user:
            user_id = event.poll_answer.user.id
        elif hasattr(event, 'my_chat_member') and event.my_chat_member and event.my_chat_member.from_user:
            user_id = event.my_chat_member.from_user.id
        elif hasattr(event, 'chat_member') and event.chat_member and event.chat_member.from_user:
            user_id = event.chat_member.from_user.id
        elif hasattr(event, 'chat_join_request') and event.chat_join_request and event.chat_join_request.from_user:
            user_id = event.chat_join_request.from_user.id
        
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
        user_id = None
        event_type = type(event).__name__
        
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
        elif hasattr(event, 'chat') and event.chat:
            user_id = event.chat.id
        elif hasattr(event, 'message') and event.message and event.message.from_user:
            user_id = event.message.from_user.id
        elif hasattr(event, 'callback_query') and event.callback_query and event.callback_query.from_user:
            user_id = event.callback_query.from_user.id
        elif hasattr(event, 'edited_message') and event.edited_message and event.edited_message.from_user:
            user_id = event.edited_message.from_user.id
        elif hasattr(event, 'channel_post') and event.channel_post and event.channel_post.chat:
            user_id = event.channel_post.chat.id
        elif hasattr(event, 'edited_channel_post') and event.edited_channel_post and event.edited_channel_post.chat:
            user_id = event.edited_channel_post.chat.id
        elif hasattr(event, 'inline_query') and event.inline_query and event.inline_query.from_user:
            user_id = event.inline_query.from_user.id
        elif hasattr(event, 'chosen_inline_result') and event.chosen_inline_result and event.chosen_inline_result.from_user:
            user_id = event.chosen_inline_result.from_user.id
        elif hasattr(event, 'shipping_query') and event.shipping_query and event.shipping_query.from_user:
            user_id = event.shipping_query.from_user.id
        elif hasattr(event, 'pre_checkout_query') and event.pre_checkout_query and event.pre_checkout_query.from_user:
            user_id = event.pre_checkout_query.from_user.id
        elif hasattr(event, 'poll_answer') and event.poll_answer and event.poll_answer.user:
            user_id = event.poll_answer.user.id
        elif hasattr(event, 'my_chat_member') and event.my_chat_member and event.my_chat_member.from_user:
            user_id = event.my_chat_member.from_user.id
        elif hasattr(event, 'chat_member') and event.chat_member and event.chat_member.from_user:
            user_id = event.chat_member.from_user.id
        elif hasattr(event, 'chat_join_request') and event.chat_join_request and event.chat_join_request.from_user:
            user_id = event.chat_join_request.from_user.id
            
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
                    await event.reply(
                        "An error occurred while processing your request. Please try running the /start command to register in the system."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer()
                    await event.message.reply(
                        "An error occurred while processing your request. Please try running the /start command to register in the system."
                    )
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
                await event.reply(
                    "An unexpected error occurred. Please try again later or contact the administrator."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer()
                await event.message.reply(
                    "An unexpected error occurred. Please try again later or contact the administrator."
                )


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
        await ensure_admin_users(session) # Call the new function here

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
