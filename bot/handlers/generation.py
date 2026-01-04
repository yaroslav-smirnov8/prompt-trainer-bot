from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import FSInputFile
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from bot.states import UserStates
from bot.keyboards import get_back_to_menu_keyboard, get_generation_type_keyboard, get_prompt_evaluation_keyboard, MenuCallback, PromptEvaluationCallback
from database import crud
from services.ai_service import AIGenerationService, evaluate_prompt_quality, calculate_rating_bonus

router = Router()


@router.callback_query(MenuCallback.filter(F.action == "generate_text"))
async def text_generation_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handles text generation type selection."""
    import traceback

    telegram_id = callback.from_user.id if callback.from_user else None
    username = callback.from_user.username if callback.from_user else None

    logger.info(f"generation.text_generation_callback: Processing gen_type:text callback for telegram_id={telegram_id}, username={username}")

    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"generation.text_generation_callback: SUSPICIOUS - Processing callback for telegram_id=1!")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"generation.text_generation_callback: Stack trace for telegram_id=1 detection:\n{stack_trace}")

    try:
        logger.info(f"generation.text_generation_callback: Answering callback for telegram_id={telegram_id}")
        await callback.answer()

        logger.info(f"generation.text_generation_callback: Getting user data for telegram_id={telegram_id}")
        user = await crud.get_user(session, telegram_id)

        if not user:
            logger.error(f"generation.text_generation_callback: User with telegram_id={telegram_id} not found")
            await callback.message.answer(
                "An error occurred while retrieving user data. Please try again later.",
                reply_markup=get_back_to_menu_keyboard()
            )
            return
        
        logger.info(f"generation.text_generation_callback: Found user with id={user.id}, is_admin={user.is_admin}")

        # Check for administrator
        if not user.is_admin:
            logger.info(f"generation.text_generation_callback: User is not admin, checking generation limits")

            # Reset daily generation limit if a new day has started
            if user.last_generation_date.date() < datetime.utcnow().date():
                logger.info(f"generation.text_generation_callback: Resetting daily generation limit for telegram_id={telegram_id}")
                await crud.update_user(session, user.user_id, {"daily_generations_left": 5, "last_generation_date": datetime.utcnow()})
                user = await crud.get_user(session, telegram_id)
                logger.info(f"generation.text_generation_callback: Reset daily_generations_left to 5 for telegram_id={telegram_id}")

            logger.info(f"generation.text_generation_callback: User has {user.daily_generations_left} generations left")
            if user.daily_generations_left <= 0:
                logger.info(f"generation.text_generation_callback: User has no generations left, sending limit message")
                await callback.message.answer(
                    "You have exhausted your daily generation limit. Try again tomorrow.",
                    reply_markup=get_back_to_menu_keyboard()
                )
                return

            logger.info(f"generation.text_generation_callback: Setting state to UserStates.entering_prompt for telegram_id={telegram_id}")
            await state.set_state(UserStates.entering_prompt)

            logger.info(f"generation.text_generation_callback: Sending prompt request message with {user.daily_generations_left} generations left")
            await callback.message.answer(f"You have {user.daily_generations_left} generations left today. Enter your prompt for text generation:")
        else:
            logger.info(f"generation.text_generation_callback: User is admin, unlimited generations")
            # Unlimited generation for administrators
            logger.info(f"generation.text_generation_callback: Setting state to UserStates.entering_prompt for admin telegram_id={telegram_id}")
            await state.set_state(UserStates.entering_prompt)

            logger.info(f"generation.text_generation_callback: Sending admin prompt request message")
            await callback.message.answer("Enter your prompt for text generation (admin mode - unlimited):")

        logger.info(f"generation.text_generation_callback: Successfully processed text generation callback for telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"generation.text_generation_callback: Error processing callback for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        logger.error(f"generation.text_generation_callback: Stack trace for callback error:\n{traceback.format_exc()}")

        # Try to respond to user
        try:
            await callback.message.answer(
                "An error occurred while processing the request. Please try again later.",
                reply_markup=get_back_to_menu_keyboard()
            )
        except Exception as answer_error:
            logger.error(f"generation.text_generation_callback: Failed to send error message: {answer_error}")


@router.callback_query(MenuCallback.filter(F.action == "generate_image"))
async def image_generation_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handles image generation type selection."""
    import traceback

    telegram_id = callback.from_user.id if callback.from_user else None
    username = callback.from_user.username if callback.from_user else None

    logger.info(f"generation.image_generation_callback: Processing gen_type:image callback for telegram_id={telegram_id}, username={username}")

    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"generation.image_generation_callback: SUSPICIOUS - Processing callback for telegram_id=1!")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"generation.image_generation_callback: Stack trace for telegram_id=1 detection:\n{stack_trace}")

    try:
        logger.info(f"generation.image_generation_callback: Answering callback for telegram_id={telegram_id}")
        await callback.answer()

        logger.info(f"generation.image_generation_callback: Getting user data for telegram_id={telegram_id}")
        user = await crud.get_user(session, telegram_id)

        if not user:
            logger.error(f"generation.image_generation_callback: User with telegram_id={telegram_id} not found")
            await callback.message.answer(
                "An error occurred while retrieving user data. Please try again later.",
                reply_markup=get_back_to_menu_keyboard()
            )
            return

        logger.info(f"generation.image_generation_callback: Found user with id={user.id}, is_admin={user.is_admin}")

        # Check for administrator
        if not user.is_admin:
            logger.info(f"generation.image_generation_callback: User is not admin, checking generation limits")

            # Reset daily generation limit if a new day has started
            if user.last_generation_date.date() < datetime.utcnow().date():
                logger.info(f"generation.image_generation_callback: Resetting daily generation limit for telegram_id={telegram_id}")
                await crud.update_user(session, user.user_id, {"daily_generations_left": 5, "last_generation_date": datetime.utcnow()})
                user = await crud.get_user(session, telegram_id)
                logger.info(f"generation.image_generation_callback: Reset daily_generations_left to 5 for telegram_id={telegram_id}")

            logger.info(f"generation.image_generation_callback: User has {user.daily_generations_left} generations left")
            if user.daily_generations_left <= 0:
                logger.info(f"generation.image_generation_callback: User has no generations left, sending limit message")
                await callback.message.answer(
                    "You have exhausted your daily generation limit. Try again tomorrow.",
                    reply_markup=get_back_to_menu_keyboard()
                )
                return

            logger.info(f"generation.image_generation_callback: Setting state to UserStates.entering_image_prompt for telegram_id={telegram_id}")
            await state.set_state(UserStates.entering_image_prompt)

            logger.info(f"generation.image_generation_callback: Sending prompt request message with {user.daily_generations_left} generations left")
            await callback.message.answer(f"You have {user.daily_generations_left} generations left today.\n\nEnter your prompt for image generation:", parse_mode="HTML")
        else:
            logger.info(f"generation.image_generation_callback: User is admin, unlimited generations")
            # Unlimited generation for administrators
            logger.info(f"generation.image_generation_callback: Setting state to UserStates.entering_image_prompt for admin telegram_id={telegram_id}")
            await state.set_state(UserStates.entering_image_prompt)

            logger.info(f"generation.image_generation_callback: Sending admin prompt request message")
            await callback.message.answer("Enter your prompt for image generation (admin mode - unlimited):")

        logger.info(f"generation.image_generation_callback: Successfully processed image generation callback for telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"generation.image_generation_callback: Error processing callback for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        logger.error(f"generation.image_generation_callback: Stack trace for callback error:\n{traceback.format_exc()}")

        # Try to respond to user
        try:
            await callback.message.answer(
                "An error occurred while processing the request. Please try again later.",
                reply_markup=get_back_to_menu_keyboard()
            )
        except Exception as answer_error:
            logger.error(f"generation.image_generation_callback: Failed to send error message: {answer_error}")



@router.message(UserStates.entering_image_prompt)
async def evaluate_image_prompt(message: Message, state: FSMContext, session: AsyncSession):
    """Evaluates the user's image prompt before generation."""
    import traceback

    telegram_id = message.from_user.id if message.from_user else None
    username = message.from_user.username if message.from_user else None

    logger.info(f"generation.process_image_prompt: Processing image prompt for telegram_id={telegram_id}, username={username}")

    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"generation.process_image_prompt: SUSPICIOUS - Processing message for telegram_id=1!")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"generation.process_image_prompt: Stack trace for telegram_id=1 detection:\n{stack_trace}")

    try:

        logger.info(f"generation.evaluate_image_prompt: Getting user data for telegram_id={telegram_id}")
        user = await crud.get_user(session, telegram_id)

        if not user:
            logger.error(f"generation.evaluate_image_prompt: User with telegram_id={telegram_id} not found")
            await message.answer(
                "An error occurred while retrieving user data. Please try again later.",
                reply_markup=get_back_to_menu_keyboard()
            )
            return
        
        logger.info(f"generation.evaluate_image_prompt: Found user with id={user.id}, is_admin={user.is_admin}")

        # Store prompt in state for later use
        prompt = message.text
        await state.update_data(current_prompt=prompt, user_id=user.user_id)
        await state.set_state(UserStates.reviewing_image_prompt)
        
        logger.info(f"generation.evaluate_image_prompt: Evaluating image prompt: '{prompt[:50]}...'")
        
        # Show evaluation status message
        status_message = await message.answer(
            "🔍 <b>Analyzing your image prompt...</b>\n\n"
            f"📝 Prompt: <code>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</code>\n\n"
            "⏳ Please wait...",
            parse_mode="HTML"
        )
        
        try:
            # Evaluate prompt quality
            evaluation_result = await evaluate_prompt_quality(prompt, 'image')
            logger.info(f"generation.evaluate_image_prompt: Evaluation result: {evaluation_result}")
            
            # Delete status message
            try:
                await status_message.delete()
            except:
                pass
            
            # Create evaluation message
            ai_score = evaluation_result.get('ai_score', 0)
            technical_score = evaluation_result.get('technical_score', 0)
            structure_score = evaluation_result.get('structure_score', 0) 
            creativity_score = evaluation_result.get('creativity_score', 0)
            feedback = evaluation_result.get('feedback', 'Нет отзыва')
            improvement_suggestions = evaluation_result.get('improvement_suggestions', '')
            
            # Calculate bonus points
            bonus_points = calculate_rating_bonus(ai_score)
            
            # Format evaluation message
            score_emoji = "🔥" if ai_score >= 8 else "⭐" if ai_score >= 6 else "🎨" if ai_score >= 4 else "💡"
            
            evaluation_message = (
                f"{score_emoji} <b>Your Image Prompt Evaluation</b>\n\n"
                f"📊 <b>Overall Score:</b> {ai_score:.1f}/10\n\n"
                f"🎯 <b>Detailed Evaluation:</b>\n"
                f"• Technical Accuracy: {technical_score:.1f}/3\n"
                f"• Structure: {structure_score:.1f}/2\n"
                f"• Creativity: {creativity_score:.1f}/1\n\n"
                f"💬 <b>Feedback:</b>\n{feedback}\n\n"
            )
            
            if improvement_suggestions:
                evaluation_message += f"💡 <b>Recommendations:</b>\n{improvement_suggestions}\n\n"
                
            if bonus_points > 0:
                evaluation_message += f"🏆 <b>Rating Bonus:</b> +{bonus_points} points\n\n"
                
            evaluation_message += "What would you like to do?"
            
            await message.answer(
                evaluation_message,
                reply_markup=get_prompt_evaluation_keyboard("image"),
                parse_mode="HTML"
            )
            
        except Exception as eval_error:
            logger.error(f"generation.evaluate_image_prompt: Error during evaluation: {eval_error}")
            # Delete status message
            try:
                await status_message.delete()
            except:
                pass
            
            await message.answer(
                "❌ <b>Prompt Evaluation Error</b>\n\n"
                "Failed to evaluate prompt. You can proceed with generation or try another prompt.",
                reply_markup=get_prompt_evaluation_keyboard("image"),
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"generation.process_image_prompt: Error processing image prompt for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        logger.error(f"generation.process_image_prompt: Stack trace for error:\n{traceback.format_exc()}")
        
        # Delete status message if it exists
        try:
            if 'status_message' in locals():
                await status_message.delete()
        except:
            pass
        
        # Try to respond to user
        try:
            await message.answer(
                "❌ <b>An Error Occurred</b>\n\n"
                "An error occurred while processing the request. Please try again later.",
                reply_markup=get_back_to_menu_keyboard(),
                parse_mode="HTML"
            )
        except Exception as answer_error:
            logger.error(f"generation.process_image_prompt: Failed to send error message: {answer_error}")



@router.callback_query(MenuCallback.filter(F.action == "generate"))
async def generation_callback_handler(callback: CallbackQuery, state: FSMContext):
    """Handles the generation button press and shows generation type selection."""

    import traceback
    
    telegram_id = callback.from_user.id if callback.from_user else None
    username = callback.from_user.username if callback.from_user else None
    
    logger.info(f"generation.generation_callback_handler: Processing generation button press for telegram_id={telegram_id}, username={username}")
    
    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"generation.generation_callback_handler: SUSPICIOUS - Processing callback for telegram_id=1!")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"generation.generation_callback_handler: Stack trace for telegram_id=1 detection:\n{stack_trace}")
    
    try:
        logger.info(f"generation.generation_callback_handler: Answering callback for telegram_id={telegram_id}")
        await callback.answer()
        
        logger.info(f"generation.generation_callback_handler: Showing generation type selection for telegram_id={telegram_id}")
        await callback.message.edit_text(
            "Choose generation type:",
            reply_markup=get_generation_type_keyboard()
        )
        await state.set_state(UserStates.choosing_generation_type)
        logger.info(f"generation.generation_callback_handler: Successfully showed generation type selection to telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"generation.generation_callback_handler: Error showing generation type selection for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        logger.error(f"generation.generation_callback_handler: Stack trace for error:\n{traceback.format_exc()}")
        
        # Try to respond to user
        try:
            await callback.message.answer(
                "An error occurred while processing the request. Please try again later.",
                reply_markup=get_back_to_menu_keyboard()
            )
        except Exception as answer_error:
            logger.error(f"generation.generation_callback_handler: Failed to send error message: {answer_error}")



@router.message(UserStates.entering_prompt)
async def evaluate_text_prompt(message: Message, state: FSMContext, session: AsyncSession):
    """Evaluates the user's text prompt before generation."""

    import traceback
    
    telegram_id = message.from_user.id if message.from_user else None
    username = message.from_user.username if message.from_user else None
    
    logger.info(f"generation.process_prompt: Processing text prompt for telegram_id={telegram_id}, username={username}")
    
    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"generation.process_prompt: SUSPICIOUS - Processing message for telegram_id=1!")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"generation.process_prompt: Stack trace for telegram_id=1 detection:\n{stack_trace}")
    
    try:
        logger.info(f"generation.evaluate_text_prompt: Getting user data for telegram_id={telegram_id}")
        user = await crud.get_user(session, telegram_id)
        
        if not user:
            logger.error(f"generation.evaluate_text_prompt: User with telegram_id={telegram_id} not found")
            await message.answer(
                "An error occurred while retrieving user data. Please try again later.",
                reply_markup=get_back_to_menu_keyboard()
            )
            return
        
        logger.info(f"generation.evaluate_text_prompt: Found user with id={user.id}, is_admin={user.is_admin}")

        # Store prompt in state for later use
        prompt = message.text
        await state.update_data(current_prompt=prompt, user_id=user.user_id)
        await state.set_state(UserStates.reviewing_text_prompt)
        
        logger.info(f"generation.evaluate_text_prompt: Evaluating text prompt: '{prompt[:50]}...'")
        
        # Show evaluation status message
        status_message = await message.answer(
            "🔍 <b>Analyzing your prompt...</b>\n\n"
            f"📝 Prompt: <code>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</code>\n\n"
            "⏳ Please wait...",
            parse_mode="HTML"
        )
        
        try:
            # Evaluate prompt quality
            evaluation_result = await evaluate_prompt_quality(prompt, 'text')
            logger.info(f"generation.evaluate_text_prompt: Evaluation result: {evaluation_result}")
            
            # Delete status message
            try:
                await status_message.delete()
            except:
                pass
            
            # Create evaluation message
            ai_score = evaluation_result.get('ai_score', 0)
            clarity_score = evaluation_result.get('clarity_score', 0)
            structure_score = evaluation_result.get('structure_score', 0) 
            creativity_score = evaluation_result.get('creativity_score', 0)
            feedback = evaluation_result.get('feedback', 'Нет отзыва')
            improvement_suggestions = evaluation_result.get('improvement_suggestions', '')
            
            # Calculate bonus points
            bonus_points = calculate_rating_bonus(ai_score)
            
            # Format evaluation message
            score_emoji = "🔥" if ai_score >= 8 else "⭐" if ai_score >= 6 else "📝" if ai_score >= 4 else "💡"
            
            evaluation_message = (
                f"{score_emoji} <b>Your Prompt Evaluation</b>\n\n"
                f"📊 <b>Overall Score:</b> {ai_score:.1f}/10\n\n"
                f"🎯 <b>Detailed Evaluation:</b>\n"
                f"• Clarity: {clarity_score:.1f}/3\n"
                f"• Structure: {structure_score:.1f}/2\n"
                f"• Creativity: {creativity_score:.1f}/1\n\n"
                f"💬 <b>Feedback:</b>\n{feedback}\n\n"
            )
            
            if improvement_suggestions:
                evaluation_message += f"💡 <b>Recommendations:</b>\n{improvement_suggestions}\n\n"
                
            if bonus_points > 0:
                evaluation_message += f"🏆 <b>Rating Bonus:</b> +{bonus_points} points\n\n"
                
            evaluation_message += "What would you like to do?"
            
            await message.answer(
                evaluation_message,
                reply_markup=get_prompt_evaluation_keyboard("text"),
                parse_mode="HTML"
            )
            
        except Exception as eval_error:
            logger.error(f"generation.evaluate_text_prompt: Error during evaluation: {eval_error}")
            # Delete status message
            try:
                await status_message.delete()
            except:
                pass
            
            await message.answer(
                "❌ <b>Prompt Evaluation Error</b>\n\n"
                "Failed to evaluate prompt. You can proceed with generation or try another prompt.",
                reply_markup=get_prompt_evaluation_keyboard("text"),
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"generation.evaluate_text_prompt: Error evaluating text prompt for telegram_id={telegram_id}: {e}")
        logger.error(f"generation.evaluate_text_prompt: Stack trace: {traceback.format_exc()}")
        
        try:
            await message.answer(
                "An error occurred while evaluating the prompt. Please try again later.",
                reply_markup=get_back_to_menu_keyboard()
            )
        except Exception as answer_error:
            logger.error(f"generation.evaluate_text_prompt: Failed to send error message: {answer_error}")


# Handlers for prompt evaluation buttons
@router.callback_query(PromptEvaluationCallback.filter(F.action == "proceed"))
async def proceed_with_generation(callback: CallbackQuery, callback_data: PromptEvaluationCallback, state: FSMContext, session: AsyncSession):
    """Proceed with generation using current prompt"""

    telegram_id = callback.from_user.id
    logger.info(f"generation.proceed_with_generation: User {telegram_id} proceeding with {callback_data.prompt_type} generation")
    
    try:
        await callback.answer()
        
        # Get prompt from state
        state_data = await state.get_data()
        prompt = state_data.get('current_prompt')
        user_id = state_data.get('user_id')
        
        if not prompt:
            await callback.message.edit_text(
                "Error: prompt not found. Please start over.",
                reply_markup=get_back_to_menu_keyboard()
            )
            return
        
        # Clear state and generate
        await state.clear()
        
        if callback_data.prompt_type == "text":
            await generate_text_with_prompt(callback.message, prompt, user_id, session, is_callback=True)
        elif callback_data.prompt_type == "image":
            await generate_image_with_prompt(callback.message, prompt, user_id, session, is_callback=True)
            
    except Exception as e:
        logger.error(f"generation.proceed_with_generation: Error: {e}")
        try:
            await callback.message.answer(
                "An error occurred during generation. Please try again later.",
                reply_markup=get_back_to_menu_keyboard()
            )
        except:
            pass


@router.callback_query(PromptEvaluationCallback.filter(F.action == "improve"))
async def improve_prompt(callback: CallbackQuery, callback_data: PromptEvaluationCallback, state: FSMContext, session: AsyncSession):
    """Allow user to improve their prompt"""

    telegram_id = callback.from_user.id
    logger.info(f"generation.improve_prompt: User {telegram_id} wants to improve {callback_data.prompt_type} prompt")
    
    try:
        await callback.answer()
        
        if callback_data.prompt_type == "text":
            await state.set_state(UserStates.editing_text_prompt)
            await callback.message.edit_text(
                "✏️ <b>Improve Prompt</b>\n\n"
                "Write an improved version of your prompt for text generation:",
                parse_mode="HTML"
            )
        elif callback_data.prompt_type == "image":
            await state.set_state(UserStates.editing_image_prompt)
            await callback.message.edit_text(
                "✏️ <b>Improve Prompt</b>\n\n"
                ""
                "Write an improved version of your prompt for image generation:",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"generation.improve_prompt: Error: {e}")
        try:
            await callback.message.answer(
                "An error occurred. Please try again later.",
                reply_markup=get_back_to_menu_keyboard()
            )
        except:
            pass


# Handle improved text prompts
@router.message(UserStates.editing_text_prompt)
async def handle_improved_text_prompt(message: Message, state: FSMContext, session: AsyncSession):
    """Handle user's improved text prompt"""
    # Reuse the evaluation logic
    await evaluate_text_prompt(message, state, session)


# Handle improved image prompts  
@router.message(UserStates.editing_image_prompt)
async def handle_improved_image_prompt(message: Message, state: FSMContext, session: AsyncSession):
    """Handle user's improved image prompt"""
    # Reuse the evaluation logic
    await evaluate_image_prompt(message, state, session)


async def generate_text_with_prompt(message_or_callback, prompt: str, user_id: int, session: AsyncSession, is_callback: bool = False):
    """Generate text using the provided prompt after evaluation"""

    import traceback
    
    logger.info(f"generation.generate_text_with_prompt: Generating text for user_id={user_id}")
    
    try:
        # Get user
        user = await crud.get_user(session, user_id)
        if not user:
            error_msg = "Error: user not found."
            if is_callback:
                await message_or_callback.edit_text(error_msg, reply_markup=get_back_to_menu_keyboard())
            else:
                await message_or_callback.answer(error_msg, reply_markup=get_back_to_menu_keyboard())
            return

        # Check generation limits for non-admins
        if not user.is_admin:
            # Reset daily limit if new day
            if user.last_generation_date.date() < datetime.utcnow().date():
                await crud.update_user(session, user.user_id, {"daily_generations_left": 5, "last_generation_date": datetime.utcnow()})
                user = await crud.get_user(session, user_id)

            if user.daily_generations_left <= 0:
                error_msg = "You have exhausted your daily generation limit. Try again tomorrow."
                if is_callback:
                    await message_or_callback.edit_text(error_msg, reply_markup=get_back_to_menu_keyboard())
                else:
                    await message_or_callback.answer(error_msg, reply_markup=get_back_to_menu_keyboard())
                return

            # Decrement generation count
            await crud.update_user(session, user.user_id, {"daily_generations_left": user.daily_generations_left - 1})

        # Show generation status
        status_msg = (
            "🔄 <b>Generating Text...</b>\n\n"
            f"📝 Prompt: <code>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</code>\n\n"
            "⏳ Please wait..."
        )
        
        if is_callback:
            await message_or_callback.edit_text(status_msg, parse_mode="HTML")
        else:
            status_message = await message_or_callback.answer(status_msg, parse_mode="HTML")

        # Generate text
        service = AIGenerationService()
        success, generated_text = await service.generate_text(prompt)

        if not success:
            error_msg = f"❌ <b>Generation Error:</b>\n\n{generated_text}"
            if is_callback:
                await message_or_callback.edit_text(error_msg, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
            else:
                await status_message.delete()
                await message_or_callback.answer(error_msg, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
            return

        # Save to database
        try:
            await crud.create_generated_prompt(
                session,
                user_id=user.user_id,
                prompt_text=prompt,
                result=generated_text,
                prompt_type='text'
            )
        except Exception as db_error:
            logger.error(f"generation.generate_text_with_prompt: DB error: {db_error}")

        # Evaluate and save prompt rating (in background)
        try:
            evaluation_result = await evaluate_prompt_quality(prompt, 'text')
            await crud.create_prompt_rating(
                session,
                user_id=user.user_id,
                prompt_text=prompt,
                prompt_type='text',
                evaluation_data=evaluation_result
            )
            
            # Award bonus points
            bonus_points = calculate_rating_bonus(evaluation_result.get('ai_score', 0))
            if bonus_points > 0:
                await crud.create_rating_bonus(
                    session,
                    user_id=user.user_id,
                    bonus_type='prompt_quality',
                    points=bonus_points,
                    reason=f"Quality text prompt (score: {evaluation_result.get('ai_score', 0):.1f}/10)"
                )
        except Exception as eval_error:
            logger.warning(f"generation.generate_text_with_prompt: Evaluation error: {eval_error}")

        # Clean and format text
        clean_text = generated_text
        if "<!DOCTYPE html>" in generated_text or "<html>" in generated_text:
            import re, html
            clean_text = re.sub(r'<[^>]+>', '', generated_text)
            clean_text = html.unescape(clean_text).strip()[:4000]
            if len(clean_text.strip()) < 10:
                clean_text = "Sorry, the generation service returned an incorrect response. Please try again."

        # Send result
        result_msg = f"✅ <b>Generation Result:</b>\n\n{clean_text}"
        
        if is_callback:
            await message_or_callback.edit_text(result_msg, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
        else:
            try:
                await status_message.delete()
            except:
                pass
            await message_or_callback.answer(result_msg, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"generation.generate_text_with_prompt: Error: {e}")
        logger.error(f"generation.generate_text_with_prompt: Stack trace: {traceback.format_exc()}")
        
        error_msg = "An error occurred during generation. Please try again later."
        try:
            if is_callback:
                await message_or_callback.edit_text(error_msg, reply_markup=get_back_to_menu_keyboard())
            else:
                await message_or_callback.answer(error_msg, reply_markup=get_back_to_menu_keyboard())
        except:
            pass


async def generate_image_with_prompt(message_or_callback, prompt: str, user_id: int, session: AsyncSession, is_callback: bool = False):
    """Generate image using the provided prompt after evaluation"""

    import traceback
    
    logger.info(f"generation.generate_image_with_prompt: Generating image for user_id={user_id}")
    
    try:
        # Get user
        user = await crud.get_user(session, user_id)
        if not user:
            error_msg = "Error: user not found."
            if is_callback:
                await message_or_callback.edit_text(error_msg, reply_markup=get_back_to_menu_keyboard())
            else:
                await message_or_callback.answer(error_msg, reply_markup=get_back_to_menu_keyboard())
            return

        # Check generation limits for non-admins
        if not user.is_admin:
            # Reset daily limit if new day
            if user.last_generation_date.date() < datetime.utcnow().date():
                await crud.update_user(session, user.user_id, {"daily_generations_left": 5, "last_generation_date": datetime.utcnow()})
                user = await crud.get_user(session, user_id)

            if user.daily_generations_left <= 0:
                error_msg = "You have exhausted your daily generation limit. Try again tomorrow."
                if is_callback:
                    await message_or_callback.edit_text(error_msg, reply_markup=get_back_to_menu_keyboard())
                else:
                    await message_or_callback.answer(error_msg, reply_markup=get_back_to_menu_keyboard())
                return

            # Decrement generation count
            await crud.update_user(session, user.user_id, {"daily_generations_left": user.daily_generations_left - 1})

        # Show generation status
        status_msg = (
            "🎨 <b>Generating Image...</b>\n\n"
            f"📝 Prompt: <code>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</code>\n\n"
            "⏳ Please wait, your image is being generated..."
        )
        
        if is_callback:
            await message_or_callback.edit_text(status_msg, parse_mode="HTML")
        else:
            status_message = await message_or_callback.answer(status_msg, parse_mode="HTML")

        # Generate image
        service = AIGenerationService()
        success, result = await service.generate_image(prompt=prompt)

        if not success or not result or (isinstance(result, str) and result.startswith("https://placehold.co")):
            error_msg = (
                "❌ <b>Image Generation Error</b>\n\n"
                "Failed to generate image. Please try again with a different prompt."
            )
            if is_callback:
                await message_or_callback.edit_text(error_msg, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
            else:
                await status_message.delete()
                await message_or_callback.answer(error_msg, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
            return

        # Если результат - путь к файлу, используем FSInputFile, иначе - URL
        if isinstance(result, str) and result.startswith('http'):
            image_url = result
        else:
            # Если результат - путь к файлу
            image_url = result

        # Save to database
        try:
            await crud.create_generated_prompt(
                session,
                user_id=user.user_id,
                prompt_text=prompt,
                result=image_url,
                prompt_type='image'
            )
        except Exception as db_error:
            logger.error(f"generation.generate_image_with_prompt: DB error: {db_error}")

        # Evaluate and save prompt rating (in background)
        try:
            evaluation_result = await evaluate_prompt_quality(prompt, 'image')
            await crud.create_prompt_rating(
                session,
                user_id=user.user_id,
                prompt_text=prompt,
                prompt_type='image',
                evaluation_data=evaluation_result
            )

            # Award bonus points
            bonus_points = calculate_rating_bonus(evaluation_result.get('ai_score', 0))
            if bonus_points > 0:
                await crud.create_rating_bonus(
                    session,
                    user_id=user.user_id,
                    bonus_type='prompt_quality',
                    points=bonus_points,
                    reason=f"Quality image prompt (score: {evaluation_result.get('ai_score', 0):.1f}/10)"
                )
        except Exception as eval_error:
            logger.warning(f"generation.generate_image_with_prompt: Evaluation error: {eval_error}")

        # Send result
        caption = f"🖼️ <b>Generation Result</b>\n\n📝 Prompt: <code>{prompt[:100]}{'...' if len(prompt) > 100 else ''}</code>"

        if is_callback:
            # For callback, we need to send a new message with photo
            await message_or_callback.edit_text("✅ Image ready!")
            try:
                if isinstance(image_url, str) and image_url.startswith('http'):
                    # URL image
                    await message_or_callback.answer_photo(
                        photo=image_url,
                        caption=caption,
                        reply_markup=get_back_to_menu_keyboard(),
                        parse_mode="HTML"
                    )
                else:
                    # Local file
                    photo = FSInputFile(image_url)
                    await message_or_callback.answer_photo(
                        photo=photo,
                        caption=caption,
                        reply_markup=get_back_to_menu_keyboard(),
                        parse_mode="HTML"
                    )
            except Exception as send_error:
                logger.error(f"generation.generate_image_with_prompt: Error sending photo: {send_error}")
                if isinstance(image_url, str) and image_url.startswith('http'):
                    await message_or_callback.answer(
                        f"🖼️ <b>Image Generated!</b>\n\n📝 Prompt: <code>{prompt}</code>\n\n🔗 <a href=\"{image_url}\">Open Image</a>",
                        reply_markup=get_back_to_menu_keyboard(),
                        parse_mode="HTML"
                    )
                else:
                    await message_or_callback.answer(
                        f"🖼️ <b>Image Generated!</b>\n\n📝 Prompt: <code>{prompt}</code>\n\nImage saved at: {image_url}",
                        reply_markup=get_back_to_menu_keyboard(),
                        parse_mode="HTML"
                    )
        else:
            try:
                await status_message.delete()
            except:
                pass
            try:
                if isinstance(image_url, str) and image_url.startswith('http'):
                    # URL image
                    await message_or_callback.answer_photo(
                        photo=image_url,
                        caption=caption,
                        reply_markup=get_back_to_menu_keyboard(),
                        parse_mode="HTML"
                    )
                else:
                    # Local file
                    photo = FSInputFile(image_url)
                    await message_or_callback.answer_photo(
                        photo=photo,
                        caption=caption,
                        reply_markup=get_back_to_menu_keyboard(),
                        parse_mode="HTML"
                    )
            except Exception as send_error:
                logger.error(f"generation.generate_image_with_prompt: Error sending photo: {send_error}")
                if isinstance(image_url, str) and image_url.startswith('http'):
                    await message_or_callback.answer(
                        f"🖼️ <b>Image Generated!</b>\n\n📝 Prompt: <code>{prompt}</code>\n\n🔗 <a href=\"{image_url}\">Open Image</a>",
                        reply_markup=get_back_to_menu_keyboard(),
                        parse_mode="HTML"
                    )
                else:
                    await message_or_callback.answer(
                        f"🖼️ <b>Image Generated!</b>\n\n📝 Prompt: <code>{prompt}</code>\n\nImage saved at: {image_url}",
                        reply_markup=get_back_to_menu_keyboard(),
                        parse_mode="HTML"
                    )
            
    except Exception as e:
        logger.error(f"generation.generate_image_with_prompt: Error: {e}")
        logger.error(f"generation.generate_image_with_prompt: Stack trace: {traceback.format_exc()}")
        
        error_msg = "An error occurred during image generation. Please try again later."
        try:
            if is_callback:
                await message_or_callback.edit_text(error_msg, reply_markup=get_back_to_menu_keyboard())
            else:
                await message_or_callback.answer(error_msg, reply_markup=get_back_to_menu_keyboard())
        except:
            pass
