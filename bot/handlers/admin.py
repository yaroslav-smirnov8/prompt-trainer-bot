from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states import AdminStates
from bot.filters import AdminFilter, admin_only
from bot.keyboards import get_admin_menu_keyboard, AdminCallback, get_back_to_menu_keyboard
from database import crud
from loguru import logger # Import loguru

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext, session: AsyncSession):
    """Handle /admin command"""
    logger.info(f"admin_command: Handler triggered by /admin command from user_id={message.from_user.id}")
    
    # Get statistics
    users = await crud.get_all_users(session)
    total_users = len(users)
    admin_users = len([u for u in users if u.is_admin])
    
    await message.answer(
        f"👑 <b>Admin Panel</b>\n\n"
        f"📊 Statistics:\n"
        f"Total users: {total_users}\n"
        f"Administrators: {admin_users}\n\n"
        f"Choose an action:",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.set_state(AdminStates.menu)


@router.callback_query(AdminCallback.filter(F.action == "menu"))
async def admin_menu(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle admin menu callback"""
    logger.info(f"admin_menu: Handler triggered by callback from user_id={query.from_user.id}")
    logger.info(f"admin_menu: Raw callback data: {query.data}")
    
    await query.answer()
    
    # Get statistics
    users = await crud.get_all_users(session)
    total_users = len(users)
    admin_users = len([u for u in users if u.is_admin])
    
    await query.message.edit_text(
        f"👑 <b>Admin Panel</b>\n\n"
        f"📊 Statistics:\n"
        f"Total users: {total_users}\n"
        f"Administrators: {admin_users}\n\n"
        f"Choose an action:",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.set_state(AdminStates.menu)


@router.callback_query(AdminCallback.filter(F.action.in_(["add_user", "remove_user", "list_users"])))
@admin_only
async def admin_callback_handler(query: CallbackQuery, callback_data: AdminCallback, state: FSMContext, session: AsyncSession):
    """Handle admin menu button clicks"""
    logger.info(f"admin_callback_handler: START - Received callback. Raw data: {query.data}")
    logger.info(f"admin_callback_handler: Parsed callback_data: action={callback_data.action}, user_id={callback_data.user_id}")
    logger.info(f"admin_callback_handler: From user: {query.from_user.id} (@{query.from_user.username})")

    await query.answer() # Acknowledge the callback query immediately

    try:
        logger.debug(f"Callback data: {callback_data}")

        if callback_data.action == "add_user":
            logger.info("admin_callback_handler: Processing add_user action")
            await query.message.edit_text(
                "Enter the Telegram ID of the user you want to make an administrator:",
                reply_markup=get_back_to_menu_keyboard()
            )
            await state.set_state(AdminStates.waiting_for_user_to_add)
        elif callback_data.action == "remove_user":
            logger.info("admin_callback_handler: Processing remove_user action")
            await query.message.edit_text(
                "Enter the Telegram ID of the user whose administrator rights you want to revoke:",
                reply_markup=get_back_to_menu_keyboard()
            )
            await state.set_state(AdminStates.waiting_for_user_to_remove)
        elif callback_data.action == "list_users":
            logger.info("admin_callback_handler: Processing list_users action")
            try:
                users = await crud.get_all_users(session)
                admin_users = [u for u in users if u.is_admin]

                text = "👥 <b>Bot Users</b>\n\n"

                if admin_users:
                    text += "👑 <b>Administrators:</b>\n"
                    for user in admin_users:
                        name = user.full_name or user.username or f"ID: {user.user_id}"
                        text += f"• {name} (ID: {user.user_id})\n"
                    text += "\n"

                regular_users = [u for u in users if not u.is_admin]
                if regular_users:
                    text += "👤 <b>Regular Users:</b>\n"
                    for user in regular_users[:10]:  # Limit to first 10 to avoid message length issues
                        name = user.full_name or user.username or f"ID: {user.user_id}"
                        text += f"• {name} (ID: {user.user_id})\n"

                    if len(regular_users) > 10:
                        text += f"\n... and {len(regular_users) - 10} more users"

                await query.message.edit_text(
                    text,
                    reply_markup=get_admin_menu_keyboard()
                )
            except Exception as e:
                logger.error(f"Error listing users: {e}")
                await query.message.edit_text(
                    "❌ An error occurred while retrieving the user list",
                    reply_markup=get_admin_menu_keyboard()
                )
        else:
            logger.warning(f"admin_callback_handler: Unknown action: {callback_data.action}")
    except Exception as e:
        logger.error(f"Error in admin callback handler: {e}")
        await query.message.edit_text(
            "❌ An unexpected error occurred",
            reply_markup=get_admin_menu_keyboard()
        )



@router.message(AdminStates.waiting_for_user_to_add)
@admin_only
async def add_user_id_handler(message: Message, state: FSMContext, session: AsyncSession):
    """Handle user ID for adding admin rights"""
    logger.info(f"add_user_id_handler: Received message from user_id={message.from_user.id}, state={await state.get_state()}")
    try:
        user_id = int(message.text)
        user = await crud.get_user_safe(session, user_id)
        if user:
            await crud.set_admin_status(session, user_id, is_admin=True)
            await message.answer(
                f"User {user_id} has been successfully made an administrator.",
                reply_markup=get_admin_menu_keyboard()
            )
        else:
            await message.answer(
                f"User with ID {user_id} not found. Ask them to start the bot with the /start command first.",
                reply_markup=get_admin_menu_keyboard()
            )
        await state.set_state(AdminStates.menu)
    except ValueError:
        await message.answer(
            "Invalid ID. Please enter a numeric Telegram ID.",
            reply_markup=get_admin_menu_keyboard()
        )


@router.message(AdminStates.waiting_for_user_to_remove)
@admin_only
async def remove_user_id_handler(message: Message, state: FSMContext, session: AsyncSession):
    """Handle user ID for removing admin rights"""
    logger.info(f"remove_user_id_handler: Received message from user_id={message.from_user.id}, state={await state.get_state()}")
    try:
        user_id = int(message.text)
        user = await crud.get_user_safe(session, user_id)
        if user:
            await crud.set_admin_status(session, user_id, is_admin=False)
            await message.answer(
                f"Administrator rights have been successfully revoked from user {user_id}.",
                reply_markup=get_admin_menu_keyboard()
            )
        else:
            await message.answer(
                f"User with ID {user_id} not found.",
                reply_markup=get_admin_menu_keyboard()
            )
        await state.set_state(AdminStates.menu)
    except ValueError:
        await message.answer(
            "Invalid ID. Please enter a numeric Telegram ID.",
            reply_markup=get_admin_menu_keyboard()
        )


