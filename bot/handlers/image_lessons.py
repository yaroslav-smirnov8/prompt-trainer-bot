from aiogram import Router, F, types
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from aiogram.filters import Command

from bot.keyboards import get_lessons_keyboard, get_lesson_step_navigation_keyboard, ImageLessonCallback, LessonStepCallback, MenuCallback
from database import crud

router = Router()

async def _get_lessons_menu(session: AsyncSession, user_id: int):
    
    import traceback
    
    logger.info(f"image_get_lessons_menu: Getting image lessons menu for user_id={user_id}")
    
    # Check for suspicious ID
    if user_id == 1:
        logger.critical(f"image_get_lessons_menu: SUSPICIOUS - Request for image lessons menu with user_id=1!")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"image_get_lessons_menu: Stack trace for user_id=1 detection:\n{stack_trace}")
    
    try:
        text = "🖼 *Image Prompt Lessons*\n\nChoose a lesson to start learning:"
        
        logger.info(f"image_get_lessons_menu: Getting lessons by type 'image' for user_id={user_id}")
        lessons = await crud.get_lessons_by_type(session, 'image')
        logger.info(f"image_get_lessons_menu: Found {len(lessons)} image lessons for user_id={user_id}")
        
        lessons_with_status = []
        for lesson in lessons:
            logger.info(f"image_get_lessons_menu: Checking completion status for lesson_id={lesson.id}, user_id={user_id}")
            try:
                is_completed = await crud.is_lesson_completed(session, user_id, lesson.id)
                logger.info(f"image_get_lessons_menu: Lesson id={lesson.id} completion status for user_id={user_id}: {is_completed}")
                
                lesson_dict = {
                    'id': lesson.id,
                    'title': lesson.title,
                    'completed': is_completed
                }
                lessons_with_status.append(lesson_dict)
            except Exception as e:
                logger.error(f"image_get_lessons_menu: Error checking completion for lesson_id={lesson.id}, user_id={user_id}: {e}")
                # Add lesson without completion status to not block the entire list
                lesson_dict = {
                    'id': lesson.id,
                    'title': lesson.title,
                    'completed': False  # Default to incomplete
                }
                lessons_with_status.append(lesson_dict)

        logger.info(f"image_get_lessons_menu: Creating keyboard for {len(lessons_with_status)} lessons for user_id={user_id}")
        keyboard = get_lessons_keyboard(lessons_with_status, 'image')
        logger.info(f"image_get_lessons_menu: Successfully created lessons menu for user_id={user_id}")
        
        return text, keyboard
    except Exception as e:
        logger.error(f"image_get_lessons_menu: Error getting lessons menu for user_id={user_id}: {e}")
        logger.error(f"image_get_lessons_menu: Stack trace:\n{traceback.format_exc()}")
        # Return basic message and empty keyboard in case of error
        text = "🖼 *Image Prompt Lessons*\n\nAn error occurred while loading lessons. Please try again later."
        keyboard = get_lessons_keyboard([], 'image')
        return text, keyboard

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(ImageLessonCallback.filter(F.action == "finish"))
async def finish_lesson(callback: CallbackQuery, callback_data: ImageLessonCallback, session: AsyncSession):
    
    import traceback
    
    telegram_id = callback.from_user.id if callback.from_user else None
    username = callback.from_user.username if callback.from_user else None
    
    logger.info(f"image_lessons.finish_lesson: Processing finish_lesson callback for telegram_id={telegram_id}, username={username}")
    
    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"image_lessons.finish_lesson: SUSPICIOUS - Processing callback for telegram_id=1!")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"image_lessons.finish_lesson: Stack trace for telegram_id=1 detection:\n{stack_trace}")
    
    try:
        lesson_id = callback_data.id
        logger.info(f"image_lessons.finish_lesson: Getting lesson with id={lesson_id}")
        
        lesson = await crud.get_lesson_by_id(session, lesson_id)
        if not lesson:
            logger.warning(f"image_lessons.finish_lesson: Lesson with id={lesson_id} not found for telegram_id={telegram_id}")
            await callback.answer("Lesson not found!", show_alert=True)
            return
        
        logger.info(f"image_lessons.finish_lesson: Found lesson with id={lesson_id}, title={lesson.title} for telegram_id={telegram_id}")

        # Mark all steps as completed for safety
        logger.info(f"image_lessons.finish_lesson: Getting lesson steps for lesson_id={lesson_id}")
        all_steps = await crud.get_lesson_steps(session, lesson_id)
        logger.info(f"image_lessons.finish_lesson: Found {len(all_steps)} steps for lesson_id={lesson_id}")
        
        for step in all_steps:
            logger.info(f"image_lessons.finish_lesson: Processing step id={step.id} for telegram_id={telegram_id}")
            progress = await crud.get_or_create_progress(session, telegram_id, step.id)
            logger.info(f"image_lessons.finish_lesson: Got progress id={progress.id}, completed={progress.completed} for step_id={step.id}")
            
            if not progress.completed:
                logger.info(f"image_lessons.finish_lesson: Marking progress id={progress.id} as completed for telegram_id={telegram_id}")
                await crud.update_progress(session, progress.id, {"completed": True})

        logger.info(f"image_lessons.finish_lesson: All steps marked as completed for telegram_id={telegram_id}, lesson_id={lesson_id}")
        await callback.answer("Congratulations! You have completed the lesson.", show_alert=True)
        
        logger.info(f"image_lessons.finish_lesson: Getting lessons menu for telegram_id={telegram_id}")
        text, keyboard = await _get_lessons_menu(session, telegram_id)
        
        logger.info(f"image_lessons.finish_lesson: Editing message with lessons menu for telegram_id={telegram_id}")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        logger.info(f"image_lessons.finish_lesson: Successfully processed finish_lesson callback for telegram_id={telegram_id}, lesson_id={lesson_id}")
    except Exception as e:
        logger.error(f"image_lessons.finish_lesson: Error processing callback for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        logger.error(f"image_lessons.finish_lesson: Stack trace for callback error:\n{traceback.format_exc()}")
        
        # Try to answer callback to prevent interface freeze
        try:
            await callback.answer("An error occurred while processing the request", show_alert=True)
        except Exception as answer_error:
            logger.error(f"image_lessons.finish_lesson: Failed to answer callback: {answer_error}")



@router.callback_query(ImageLessonCallback.filter(F.action == "show"))
async def show_lesson(callback: CallbackQuery, callback_data: ImageLessonCallback, session: AsyncSession):
    
    import traceback
    
    telegram_id = callback.from_user.id if callback.from_user else None
    username = callback.from_user.username if callback.from_user else None
    
    logger.info(f"image_lessons.show_lesson: Processing show_lesson callback for telegram_id={telegram_id}, username={username}")
    
    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"image_lessons.show_lesson: SUSPICIOUS - Processing callback for telegram_id=1!")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"image_lessons.show_lesson: Stack trace for telegram_id=1 detection:\n{stack_trace}")
    
    try:
        lesson_id = callback_data.id
        logger.info(f"image_lessons.show_lesson: Getting lesson with id={lesson_id} for telegram_id={telegram_id}")
        
        lesson = await crud.get_lesson_by_id(session, lesson_id)
        if not lesson:
            logger.warning(f"image_lessons.show_lesson: Lesson with id={lesson_id} not found for telegram_id={telegram_id}")
            await callback.answer("Lesson not found!", show_alert=True)
            return
        
        logger.info(f"image_lessons.show_lesson: Found lesson with id={lesson_id}, title={lesson.title} for telegram_id={telegram_id}")

        logger.info(f"image_lessons.show_lesson: Getting next step for telegram_id={telegram_id}, lesson_id={lesson_id}")
        current_step = await crud.get_next_step_for_user(session, telegram_id, lesson_id)
        
        if not current_step:
            logger.info(f"image_lessons.show_lesson: No next step found for telegram_id={telegram_id}, lesson_id={lesson_id} - lesson already completed")
            await callback.answer("You have already completed this lesson!", show_alert=True)
            return
        
        logger.info(f"image_lessons.show_lesson: Found step id={current_step.id}, number={current_step.step_number} for telegram_id={telegram_id}")

        total_steps = len(lesson.steps)
        logger.info(f"image_lessons.show_lesson: Total steps for lesson_id={lesson_id}: {total_steps}")
        
        keyboard = get_lesson_step_navigation_keyboard(lesson.id, current_step.step_number, total_steps, 'image')
        logger.info(f"image_lessons.show_lesson: Created navigation keyboard for step {current_step.step_number}/{total_steps}")
        
        logger.info(f"image_lessons.show_lesson: Editing message with lesson content for telegram_id={telegram_id}")
        await callback.message.edit_text(
            f"*Lesson: {lesson.title}*\n\n{current_step.content}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        logger.info(f"image_lessons.show_lesson: Answering callback for telegram_id={telegram_id}")
        await callback.answer()
        logger.info(f"image_lessons.show_lesson: Successfully processed show_lesson callback for telegram_id={telegram_id}, lesson_id={lesson_id}")
    except Exception as e:
        logger.error(f"image_lessons.show_lesson: Error processing callback for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        logger.error(f"image_lessons.show_lesson: Stack trace for callback error:\n{traceback.format_exc()}")
        
        # Try to answer callback to prevent interface freeze
        try:
            await callback.answer("An error occurred while processing the request", show_alert=True)
        except Exception as answer_error:
            logger.error(f"image_lessons.show_lesson: Failed to answer callback: {answer_error}")


@router.callback_query(MenuCallback.filter(F.action == "image_lessons"))
async def list_lessons_callback(callback: CallbackQuery, session: AsyncSession):
    
    telegram_id = callback.from_user.id if callback.from_user else None
    username = callback.from_user.username if callback.from_user else None
    
    logger.info(f"image_list_lessons_callback: Processing list_image_lessons callback for telegram_id={telegram_id}, username={username}")
    
    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"image_list_lessons_callback: SUSPICIOUS - User with telegram_id=1 detected!")
        # Log additional debug information
        import traceback
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"image_list_lessons_callback: Stack trace for telegram_id=1 detection:\n{stack_trace}")
    
    try:
        logger.info(f"image_list_lessons_callback: Getting lessons menu for telegram_id={telegram_id}")
        text, keyboard = await _get_lessons_menu(session, telegram_id)
        
        logger.info(f"image_list_lessons_callback: Editing message with lessons menu for telegram_id={telegram_id}")
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        
        logger.info(f"image_list_lessons_callback: Answering callback for telegram_id={telegram_id}")
        await callback.answer()
        logger.info(f"image_list_lessons_callback: Successfully processed callback for telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"image_list_lessons_callback: Error processing callback for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        import traceback
        logger.error(f"image_list_lessons_callback: Stack trace for callback error:\n{traceback.format_exc()}")
        
        # Try to answer callback to prevent interface freeze
        try:
            await callback.answer("An error occurred while loading lessons", show_alert=True)
        except Exception:
            logger.error(f"image_list_lessons_callback: Failed to answer callback for telegram_id={telegram_id}")
            pass


@router.callback_query(LessonStepCallback.filter(F.action == "next"))
async def next_lesson_step(callback: CallbackQuery, callback_data: LessonStepCallback, session: AsyncSession):
    
    import traceback
    
    telegram_id = callback.from_user.id if callback.from_user else None
    username = callback.from_user.username if callback.from_user else None
    
    logger.info(f"image_lessons.next_lesson_step: Processing next_step callback for telegram_id={telegram_id}, username={username}")
    
    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"image_lessons.next_lesson_step: SUSPICIOUS - Processing callback for telegram_id=1!")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"image_lessons.next_lesson_step: Stack trace for telegram_id=1 detection:\n{stack_trace}")
    
    try:
        lesson_id = callback_data.lesson_id
        current_step_num = callback_data.step_number
        
        logger.info(f"image_lessons.next_lesson_step: Processing step {current_step_num} for lesson_id={lesson_id}, telegram_id={telegram_id}")
        
        logger.info(f"image_lessons.next_lesson_step: Getting lesson with id={lesson_id}")
        lesson = await crud.get_lesson_by_id(session, lesson_id)
        
        if not lesson:
            logger.warning(f"image_lessons.next_lesson_step: Lesson with id={lesson_id} not found for telegram_id={telegram_id}")
            await callback.answer("Lesson not found!", show_alert=True)
            return
        
        logger.info(f"image_lessons.next_lesson_step: Found lesson with id={lesson_id}, title={lesson.title} for telegram_id={telegram_id}")

        # Mark current step as completed
        logger.info(f"image_lessons.next_lesson_step: Getting current step {current_step_num} for lesson_id={lesson_id}")
        current_step_db = await crud.get_lesson_step_by_number(session, lesson_id, current_step_num)
        
        if current_step_db:
            logger.info(f"image_lessons.next_lesson_step: Found current step id={current_step_db.id} for lesson_id={lesson_id}")
            logger.info(f"image_lessons.next_lesson_step: Getting or creating progress for telegram_id={telegram_id}, step_id={current_step_db.id}")
            progress = await crud.get_or_create_progress(session, telegram_id, current_step_db.id)
            
            if not progress.completed:
                logger.info(f"image_lessons.next_lesson_step: Marking progress id={progress.id} as completed for telegram_id={telegram_id}")
                await crud.update_progress(session, progress.id, {"completed": True})
                logger.info(f"image_lessons.next_lesson_step: Successfully marked step {current_step_num} as completed")
            else:
                logger.info(f"image_lessons.next_lesson_step: Step {current_step_num} was already marked as completed")
        else:
            logger.warning(f"image_lessons.next_lesson_step: Current step {current_step_num} not found for lesson_id={lesson_id}")

        # Find next step
        logger.info(f"image_lessons.next_lesson_step: Getting next step {current_step_num + 1} for lesson_id={lesson_id}")
        next_step = await crud.get_lesson_step_by_number(session, lesson_id, current_step_num + 1)

        if not next_step:
            logger.info(f"image_lessons.next_lesson_step: No next step found - this was the last step or something went wrong")
            await callback.answer("Congratulations! You have completed the lesson.", show_alert=True)
            
            logger.info(f"image_lessons.next_lesson_step: Getting lessons menu for telegram_id={telegram_id}")
            text, keyboard = await _get_lessons_menu(session, telegram_id)
            
            logger.info(f"image_lessons.next_lesson_step: Editing message with lessons menu for telegram_id={telegram_id}")
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
            logger.info(f"image_lessons.next_lesson_step: Successfully completed lesson for telegram_id={telegram_id}")
            return

        logger.info(f"image_lessons.next_lesson_step: Found next step id={next_step.id}, number={next_step.step_number}")
        total_steps = len(lesson.steps)
        logger.info(f"image_lessons.next_lesson_step: Total steps for lesson_id={lesson_id}: {total_steps}")
        
        keyboard = get_lesson_step_navigation_keyboard(lesson.id, next_step.step_number, total_steps, 'image')
        logger.info(f"image_lessons.next_lesson_step: Created navigation keyboard for step {next_step.step_number}/{total_steps}")
        
        logger.info(f"image_lessons.next_lesson_step: Editing message with next step content for telegram_id={telegram_id}")
        await callback.message.edit_text(
            f"*Lesson: {lesson.title}*\n\n{next_step.content}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        logger.info(f"image_lessons.next_lesson_step: Answering callback for telegram_id={telegram_id}")
        await callback.answer()
        logger.info(f"image_lessons.next_lesson_step: Successfully processed next_step callback for telegram_id={telegram_id}, lesson_id={lesson_id}")
    except Exception as e:
        logger.error(f"image_lessons.next_lesson_step: Error processing callback for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        logger.error(f"image_lessons.next_lesson_step: Stack trace for callback error:\n{traceback.format_exc()}")
        
        # Try to answer callback to prevent interface freeze
        try:
            await callback.answer("An error occurred while processing the request", show_alert=True)
        except Exception as answer_error:
            logger.error(f"image_lessons.next_lesson_step: Failed to answer callback: {answer_error}")
