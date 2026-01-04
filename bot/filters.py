from aiogram.types import Message, CallbackQuery
from aiogram.filters import Filter
from sqlalchemy.ext.asyncio import AsyncSession
from database import crud
from functools import wraps
from typing import Callable, Any, Union, Optional
from aiogram.fsm.context import FSMContext

from loguru import logger

class AdminFilter(Filter):
    async def __call__(self, event: Message | CallbackQuery, session: AsyncSession) -> bool:
        user_id = self._extract_user_id(event)
        if user_id is None:
            logger.warning(f"AdminFilter: Could not determine user_id for event type={type(event).__name__}. Denying access.")
            return False

        logger.info(f"AdminFilter: Processing event type={type(event).__name__}, user_id={user_id}")

        user = await crud.get_user_safe(session, user_id)
        is_admin = user and user.is_admin
        logger.info(f"AdminFilter: Checking user_id={user_id}, is_admin={is_admin}")

        if isinstance(event, CallbackQuery):
            logger.info(f"AdminFilter: CallbackQuery data: {event.data}")

        return is_admin

    def _extract_user_id(self, event: Any) -> Optional[int]:
        if hasattr(event, 'from_user') and event.from_user:
            return event.from_user.id
        elif hasattr(event, 'chat') and event.chat:
            return event.chat.id
        elif hasattr(event, 'message') and event.message and event.message.from_user:
            return event.message.from_user.id
        elif hasattr(event, 'callback_query') and event.callback_query and event.callback_query.from_user:
            return event.callback_query.from_user.id
        elif hasattr(event, 'edited_message') and event.edited_message and event.edited_message.from_user:
            return event.edited_message.from_user.id
        elif hasattr(event, 'channel_post') and event.channel_post and event.channel_post.chat:
            return event.channel_post.chat.id
        elif hasattr(event, 'edited_channel_post') and event.edited_channel_post and event.edited_channel_post.chat:
            return event.edited_channel_post.chat.id
        elif hasattr(event, 'inline_query') and event.inline_query and event.inline_query.from_user:
            return event.inline_query.from_user.id
        elif hasattr(event, 'chosen_inline_result') and event.chosen_inline_result and event.chosen_inline_result.from_user:
            return event.chosen_inline_result.from_user.id
        elif hasattr(event, 'shipping_query') and event.shipping_query and event.shipping_query.from_user:
            return event.shipping_query.from_user.id
        elif hasattr(event, 'pre_checkout_query') and event.pre_checkout_query and event.pre_checkout_query.from_user:
            return event.pre_checkout_query.from_user.id
        elif hasattr(event, 'poll_answer') and event.poll_answer and event.poll_answer.user:
            return event.poll_answer.user.id
        elif hasattr(event, 'my_chat_member') and event.my_chat_member and event.my_chat_member.from_user:
            return event.my_chat_member.from_user.id
        elif hasattr(event, 'chat_member') and event.chat_member and event.chat_member.from_user:
            return event.chat_member.from_user.id
        elif hasattr(event, 'chat_join_request') and event.chat_join_request and event.chat_join_request.from_user:
            return event.chat_join_request.from_user.id
        return None


def admin_only(handler: Callable) -> Callable:
    """Decorator to restrict access to admin users only"""
    @wraps(handler)
    async def wrapper(event: Union[Message, CallbackQuery], *args, **kwargs) -> Any:
        session = kwargs.get('session')
        if not session:
            for arg in args:
                if isinstance(arg, AsyncSession):
                    session = arg
                    break
        
        if not session:
            logger.error(f"admin_only decorator: Session not found for event type={type(event).__name__}. Denying access.")
            if isinstance(event, CallbackQuery):
                await event.answer("Access error: failed to verify administrator rights.", show_alert=True)
            else:
                await event.answer("Access error: failed to verify administrator rights.")
            return
        
        user_id = AdminFilter()._extract_user_id(event) # Re-use extraction logic
        if user_id is None:
            logger.warning(f"admin_only decorator: Could not determine user_id for event type={type(event).__name__}. Denying access.")
            if isinstance(event, CallbackQuery):
                await event.answer("Access denied. Administrators only.", show_alert=True)
            else:
                await event.answer("Access denied. Administrators only.")
            return

        user = await crud.get_user_safe(session, user_id)
        is_admin = user and user.is_admin
        logger.info(f"admin_only decorator: Checking user_id={user_id}, is_admin={is_admin}")

        if not is_admin:
            if isinstance(event, CallbackQuery):
                await event.answer("Access denied. Administrators only.", show_alert=True)
            else:
                await event.answer("Access denied. Administrators only.")
            return
        
        return await handler(event, *args, **kwargs)
    
    return wrapper
