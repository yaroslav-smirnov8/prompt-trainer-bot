from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from bot.states import UserStates
from bot.keyboards import get_main_menu_keyboard, get_back_to_menu_keyboard, MenuCallback, get_generation_type_keyboard, AdminCallback
from bot.handlers.text_lessons import _get_lessons_menu as get_text_lessons_menu
from bot.handlers.image_lessons import _get_lessons_menu as get_image_lessons_menu
from bot.handlers.quiz import list_quizzes
from database import crud

# Create router
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    """Handle /start command"""
    
    telegram_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    logger.info(f"cmd_start: Processing /start command for telegram_id={telegram_id}, username={username}, full_name={full_name}")
    
    # Check if user exists in database
    try:
        user = await crud.get_user_safe(session, telegram_id)
        
        if not user:
            logger.info(f"cmd_start: User with telegram_id={telegram_id} not found, creating new user")
            
            # Check for suspicious ID
            if telegram_id == 1:
                logger.critical(f"cmd_start: SUSPICIOUS - Attempt to create user with telegram_id=1! Full message: {message}")
                # Log additional debug information
                import traceback
                stack_trace = ''.join(traceback.format_stack())
                logger.critical(f"cmd_start: Stack trace for telegram_id=1 creation attempt:\n{stack_trace}")
            
            # Register new user
            try:
                new_user = await crud.create_user(
                    session,
                    user_id=telegram_id,
                    username=username,
                    full_name=full_name
                )
                logger.info(f"cmd_start: Successfully created new user with database id={new_user.id} for telegram_id={telegram_id}")
                
                await message.answer(
                    "👋 Welcome to TrainBot!"
                    "\n\nI will help you learn to create effective prompts for text and image generation."
                    "\n\nChoose a section from the menu below:",
                    reply_markup=get_main_menu_keyboard(new_user.is_admin)
                )
            except Exception as e:
                logger.error(f"cmd_start: Error creating new user with telegram_id={telegram_id}: {e}")
                # Log stack trace for debugging
                import traceback
                logger.error(f"cmd_start: Stack trace for user creation error:\n{traceback.format_exc()}")
                await message.answer(
                    "An error occurred during registration. Please try again later or contact the administrator.",
                    reply_markup=get_main_menu_keyboard()
                )
                return
        else:
            logger.info(f"cmd_start: User found with database id={user.id}, telegram_id={user.user_id}, username={user.username}")
            await message.answer(
                f"👋 Welcome back, {user.full_name or user.username or 'friend'}!"
                "\n\nChoose a section from the menu below:",
                reply_markup=get_main_menu_keyboard(user.is_admin)
            )
        
        # Set state to menu
        await state.set_state(UserStates.menu)
        logger.info(f"cmd_start: State set to UserStates.menu for telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"cmd_start: Unexpected error processing /start for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        import traceback
        logger.error(f"cmd_start: Stack trace for unexpected error:\n{traceback.format_exc()}")
        await message.answer(
            "An unexpected error occurred. Please try again later or contact the administrator."
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🤖 <b>TrainBot - Your Prompt Engineering Trainer</b>\n\n"
        "This bot will help you learn to create effective prompts for text and image generation.\n\n"
        "<b>Available commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/menu - Return to main menu\n\n"
        "<b>Bot sections:</b>\n"
        "📚 <b>Text Prompt Lessons</b> - Learn to create effective prompts for text generation\n"
        "🖼 <b>Image Prompt Lessons</b> - Master the art of creating prompts for image generation\n"
        "🔄 <b>Generate</b> - Test your prompts in practice\n"
        "📊 <b>My Progress</b> - Track your learning progress\n\n"
        "Good luck with your learning! 🚀"
    )
    
    await message.answer(help_text, reply_markup=get_back_to_menu_keyboard())


@router.message(Command("menu"))
@router.callback_query(MenuCallback.filter(F.action == "main_menu"))
async def main_menu_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle main menu button"""
    logger.info(f"main_menu_handler: Received callback for main_menu, user_id={query.from_user.id}")

    user = await crud.get_user_safe(session, query.from_user.id)
    is_admin = user.is_admin if user else False

    try:
        await query.message.edit_text(
            "🏠 <b>Main Menu</b>\n\nChoose a section:",
            reply_markup=get_main_menu_keyboard(is_admin)
        )
    except Exception as e:
        logger.warning(f"main_menu_handler: Could not edit message, sending new message instead: {e}")
        # If we can't edit the message (e.g., it contains only media), send a new one
        await query.message.answer(
            "🏠 <b>Main Menu</b>\n\nChoose a section:",
            reply_markup=get_main_menu_keyboard(is_admin)
        )

    await state.set_state(UserStates.menu)


# Removed duplicate admin_menu_from_main_handler to keep only the correct one.
    """Handle /menu command and back_to_menu callback"""
    
    # Get user information for logging
    telegram_id = None
    event_type = type(event).__name__
    
    if isinstance(event, CallbackQuery):
        telegram_id = event.from_user.id if event.from_user else None
        username = event.from_user.username if event.from_user else None
        logger.info(f"cmd_menu: Processing back_to_menu callback for telegram_id={telegram_id}, username={username}")
        await event.answer()
        message = event.message
    else:
        telegram_id = event.from_user.id if event.from_user else None
        username = event.from_user.username if event.from_user else None
        logger.info(f"cmd_menu: Processing /menu command for telegram_id={telegram_id}, username={username}")
        message = event
    
    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"cmd_menu: SUSPICIOUS - User with telegram_id=1 detected! Event type: {event_type}")
        # Log additional debug information
        import traceback
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"cmd_menu: Stack trace for telegram_id=1 detection:\n{stack_trace}")
    
    try:
        user = await crud.get_user_safe(session, telegram_id)
        is_admin = user.is_admin if user else False
        
        logger.info(f"cmd_menu: Setting state to UserStates.menu for telegram_id={telegram_id}")
        await state.set_state(UserStates.menu)
        
        logger.info(f"cmd_menu: Sending main menu message to telegram_id={telegram_id}")
        await message.answer(
            "🏠 <b>Main Menu</b>\n\nChoose a section:",
            reply_markup=get_main_menu_keyboard(is_admin)
        )
        logger.info(f"cmd_menu: Successfully sent main menu to telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"cmd_menu: Error processing menu command for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        import traceback
        logger.error(f"cmd_menu: Stack trace for menu command error:\n{traceback.format_exc()}")
        
        # Try to send error message
        try:
            await message.answer(
                "An error occurred while processing the command. Please try again or use /start to restart the bot."
            )
        except Exception:
            logger.error(f"cmd_menu: Failed to send error message to telegram_id={telegram_id}")
            pass


@router.callback_query(MenuCallback.filter(F.action == "text_lessons"))
async def text_lessons_menu_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle text lessons menu button"""
    text, reply_markup = await get_text_lessons_menu(session, query.from_user.id)
    await query.message.edit_text(text, reply_markup=reply_markup)
    await state.set_state(UserStates.viewing_lessons)


@router.callback_query(MenuCallback.filter(F.action == "image_lessons"))
async def image_lessons_menu_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle image lessons menu button"""
    text, reply_markup = await get_image_lessons_menu(session, query.from_user.id)
    await query.message.edit_text(text, reply_markup=reply_markup)
    await state.set_state(UserStates.viewing_lessons)


@router.callback_query(MenuCallback.filter(F.action == "quiz"))
async def quiz_menu_handler(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle quiz menu button"""
    await list_quizzes(query, session)
    await state.set_state(UserStates.viewing_quizzes)


from bot.handlers.generation import generation_callback_handler

@router.callback_query(MenuCallback.filter(F.action == "generate"))
async def generate_menu_handler(query: CallbackQuery, state: FSMContext):
    """Handle generate menu button"""
    await generation_callback_handler(query, state)


@router.callback_query(MenuCallback.filter(F.action == "progress"))
async def progress_handler(query: CallbackQuery, session: AsyncSession):
    """Handle progress button"""
    
    telegram_id = query.from_user.id
    logger.info(f"progress_handler: Processing progress request for telegram_id={telegram_id}")
    
    try:
        # Get user
        user = await crud.get_user_safe(session, telegram_id)
        if not user:
            await query.answer("User not found. Please start with the /start command.", show_alert=True)
            return
        
        # Get all lessons
        text_lessons = await crud.get_lessons_by_type(session, "text")
        image_lessons = await crud.get_lessons_by_type(session, "image")
        
        # Calculate progress
        completed_text = 0
        completed_image = 0

        for lesson in text_lessons:
            if await crud.is_lesson_completed(session, telegram_id, lesson.id):
                completed_text += 1

        for lesson in image_lessons:
            if await crud.is_lesson_completed(session, telegram_id, lesson.id):
                completed_image += 1

        total_text = len(text_lessons)
        total_image = len(image_lessons)

        progress_text = (
            "📊 <b>Your Progress</b>\n\n"
            f"📚 Text Prompt Lessons: {completed_text}/{total_text}\n"
            f"🖼 Image Prompt Lessons: {completed_image}/{total_image}\n\n"
        )
        
        if total_text > 0:
            text_percentage = int((completed_text / total_text) * 100)
            progress_text += f"Text lessons: {text_percentage}% completed\n"
            
        if total_image > 0:
            image_percentage = int((completed_image / total_image) * 100)
            progress_text += f"Image lessons: {image_percentage}% completed"
        
        await query.message.edit_text(
            progress_text,
            reply_markup=get_back_to_menu_keyboard()
        )
        await query.answer()
    except Exception as e:
        logger.error(f"progress_handler: Error processing progress for telegram_id={telegram_id}: {e}")
        await query.answer("An error occurred while retrieving progress.", show_alert=True)


@router.callback_query(MenuCallback.filter(F.action == "rating"))
async def rating_handler(query: CallbackQuery, session: AsyncSession):
    """Handle rating button"""
    
    telegram_id = query.from_user.id
    logger.info(f"rating_handler: Processing rating request for telegram_id={telegram_id}")
    
    try:
        # Get user ratings
        ratings = await crud.get_user_ratings(session, top_n=10)
        
        if not ratings:
            rating_text = "🏆 <b>User Leaderboard</b>\n\nNo data available for the leaderboard yet."
        else:
            rating_text = "🏆 <b>User Leaderboard</b>\n\n"
            for i, rating in enumerate(ratings, 1):
                name = rating['full_name'] or rating['username'] or f"User {i}"
                score = rating['total_score']
                rating_text += f"{i}. {name}: {score:.1f} points\n"
        
        await query.message.edit_text(
            rating_text,
            reply_markup=get_back_to_menu_keyboard()
        )
        await query.answer()
    except Exception as e:
        logger.error(f"rating_handler: Error processing rating for telegram_id={telegram_id}: {e}")
        await query.answer("An error occurred while retrieving the leaderboard.", show_alert=True)










@router.callback_query(MenuCallback.filter(F.action == "help"))
async def help_handler(query: CallbackQuery):
    """Handle help button"""
    help_text = (
        "🤖 <b>TrainBot - Your Prompt Engineering Trainer</b>\n\n"
        "This bot will help you learn to create effective prompts for text and image generation.\n\n"
        "<b>Available sections:</b>\n"
        "📚 <b>Text Prompt Lessons</b> - Learn to create effective prompts for text generation\n"
        "🖼 <b>Image Prompt Lessons</b> - Master the art of creating prompts for image generation\n"
        "📝 <b>Quiz</b> - Test your knowledge with quizzes\n"
        "🔄 <b>Generate</b> - Test your prompts in practice\n"
        "📊 <b>My Progress</b> - Track your learning progress\n"
        "🏆 <b>Leaderboard</b> - See how you compare with other users\n\n"
        "<b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/menu - Return to main menu\n\n"
        "Good luck with your learning! 🚀"
    )

    await query.message.edit_text(
        help_text,
        reply_markup=get_back_to_menu_keyboard()
    )
    await query.answer()


