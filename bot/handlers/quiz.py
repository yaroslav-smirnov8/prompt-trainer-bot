from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from bot.states import UserStates
from bot.keyboards import get_quizzes_keyboard, get_quiz_question_keyboard, get_back_to_menu_keyboard, MenuCallback, QuizCallback, QuizActionCallback
from database import crud
from services.ai_service import evaluate_answer

router = Router()


@router.callback_query(MenuCallback.filter(F.action == "quiz"))
async def list_quizzes(query: CallbackQuery, session: AsyncSession):
    """Display all available quizzes."""
    quizzes = await crud.get_quizzes(session)
    await query.message.edit_text(
        "📝 *Quiz*\n\nChoose a quiz you want to take:",
        reply_markup=get_quizzes_keyboard(quizzes),
        parse_mode="Markdown"
    )


@router.callback_query(MenuCallback.filter(F.action == "rating"))
async def show_ratings(query: CallbackQuery, session: AsyncSession):
    """Display user ratings."""
    ratings = await crud.get_user_ratings(session)
    
    if not ratings:
        await query.answer("🏆 *Leaderboard*\n\nNo data available for the leaderboard yet.", show_alert=True)
        return
        
    response_text = "🏆 *User Leaderboard:*\n\n"
    for i, rating in enumerate(ratings, 1):
        response_text += f"{i}. {rating['full_name'] or rating['username']} - *{rating['total_score']}* points\n"
        
    await query.message.edit_text(response_text, parse_mode="Markdown", reply_markup=get_back_to_menu_keyboard())


@router.callback_query(QuizCallback.filter(F.action == "start"))
async def start_quiz(callback: CallbackQuery, callback_data: QuizCallback, state: FSMContext, session: AsyncSession):
    """Starts a quiz and shows the first question."""
    
    import traceback
    
    telegram_id = callback.from_user.id if callback.from_user else None
    username = callback.from_user.username if callback.from_user else None
    
    logger.info(f"quiz.start_quiz: Processing start_quiz callback for telegram_id={telegram_id}, username={username}")
    
    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"quiz.start_quiz: SUSPICIOUS - Processing callback for telegram_id=1!")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"quiz.start_quiz: Stack trace for telegram_id=1 detection:\n{stack_trace}")
    
    try:
        quiz_id = callback_data.id
        logger.info(f"quiz.start_quiz: Starting quiz_id={quiz_id} for telegram_id={telegram_id}")
        
        logger.info(f"quiz.start_quiz: Creating quiz attempt for telegram_id={telegram_id}, quiz_id={quiz_id}")
        attempt = await crud.create_quiz_attempt(session, user_id=telegram_id, quiz_id=quiz_id)
        logger.info(f"quiz.start_quiz: Created quiz attempt with id={attempt.id}")
        
        logger.info(f"quiz.start_quiz: Updating state data with attempt_id={attempt.id}")
        await state.update_data(attempt_id=attempt.id)
        
        logger.info(f"quiz.start_quiz: Getting questions for quiz_id={quiz_id}")
        questions = await crud.get_questions_for_quiz(session, quiz_id)
        
        if not questions:
            logger.warning(f"quiz.start_quiz: No questions found for quiz_id={quiz_id}")
            await callback.answer("This quiz has no questions yet.", show_alert=True)
            return
        
        logger.info(f"quiz.start_quiz: Found {len(questions)} questions for quiz_id={quiz_id}")
        logger.info(f"quiz.start_quiz: Setting state to UserStates.in_quiz for telegram_id={telegram_id}")
        await state.set_state(UserStates.in_quiz)
        
        logger.info(f"quiz.start_quiz: Showing first question (id={questions[0].id}) to telegram_id={telegram_id}")
        await _show_question(callback.message, state, session, questions[0])
        
        logger.info(f"quiz.start_quiz: Answering callback for telegram_id={telegram_id}")
        await callback.answer()
        logger.info(f"quiz.start_quiz: Successfully started quiz_id={quiz_id} for telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"quiz.start_quiz: Error starting quiz for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        logger.error(f"quiz.start_quiz: Stack trace for quiz start error:\n{traceback.format_exc()}")
        
        # Try to answer callback to prevent interface freeze
        try:
            await callback.answer("An error occurred while starting the quiz", show_alert=True)
        except Exception as answer_error:
            logger.error(f"quiz.start_quiz: Failed to answer callback: {answer_error}")



async def _show_question(message: Message, state: FSMContext, session: AsyncSession, question):
    """Helper function to display a question."""
    
    logger.info(f"_show_question called with question.id={question.id}, question.order={question.order}, quiz_id={question.quiz_id}")
    
    await state.update_data(current_question_id=question.id)
    logger.info(f"Updated state with current_question_id={question.id}")
    
    try:
        await message.edit_text(
            f"*Question {question.order}:*\n\n{question.question_text}",
            reply_markup=get_quiz_question_keyboard(),
            parse_mode="Markdown"
        )
        logger.info(f"Successfully displayed question {question.id} to user")
    except Exception as e:
        logger.error(f"Error displaying question: {e}")
        try:
            await message.answer(
                f"*Question {question.order}:*\n\n{question.question_text}",
                reply_markup=get_quiz_question_keyboard(),
                parse_mode="Markdown"
            )
            logger.info(f"Displayed question {question.id} using message.answer as fallback")
        except Exception as e2:
            logger.error(f"Error in fallback display method: {e2}")
            await message.answer("An error occurred while displaying the question. Try starting the quiz again.", 
                               reply_markup=get_back_to_menu_keyboard())


@router.callback_query(QuizActionCallback.filter(F.action == "cancel"))
async def cancel_quiz(callback: CallbackQuery, state: FSMContext):
    """Cancels the current quiz."""
    await state.clear()
    await callback.message.edit_text("Quiz cancelled.", reply_markup=get_back_to_menu_keyboard())
    await callback.answer()


@router.message(UserStates.in_quiz)
async def handle_answer(message: Message, state: FSMContext, session: AsyncSession):
    """Handles user's answer to a quiz question."""
    
    import traceback
    
    telegram_id = message.from_user.id if message.from_user else None
    username = message.from_user.username if message.from_user else None
    
    logger.info(f"quiz.handle_answer: Processing answer for telegram_id={telegram_id}, username={username}")
    
    # Check for suspicious ID
    if telegram_id == 1:
        logger.critical(f"quiz.handle_answer: SUSPICIOUS - Processing answer for telegram_id=1!")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"quiz.handle_answer: Stack trace for telegram_id=1 detection:\n{stack_trace}")
    
    try:
        logger.info(f"quiz.handle_answer: Getting state data for telegram_id={telegram_id}")
        data = await state.get_data()
        attempt_id = data.get("attempt_id")
        question_id = data.get("current_question_id")
        user_answer_text = message.text
        
        logger.info(f"quiz.handle_answer: Got attempt_id={attempt_id}, question_id={question_id} for telegram_id={telegram_id}")

        if not attempt_id or not question_id:
            logger.warning(f"quiz.handle_answer: Missing attempt_id or question_id for telegram_id={telegram_id}")
            await message.answer("An error occurred. Try starting the quiz again.", reply_markup=get_back_to_menu_keyboard())
            logger.info(f"quiz.handle_answer: Clearing state for telegram_id={telegram_id} due to missing data")
            await state.clear()
            return

        # Save user's answer
        logger.info(f"quiz.handle_answer: Creating user answer for attempt_id={attempt_id}, question_id={question_id}, telegram_id={telegram_id}")
        user_answer = await crud.create_user_answer(session, attempt_id, question_id, user_answer_text)
        logger.info(f"quiz.handle_answer: Created user answer with id={user_answer.id}")

        # Evaluate the answer using g4f
        logger.info(f"quiz.handle_answer: Getting question details for question_id={question_id}")
        question = await session.get(crud.Question, question_id)
        if not question:
            logger.error(f"quiz.handle_answer: Question with id={question_id} not found for telegram_id={telegram_id}")
            await message.answer("An error occurred while retrieving the question. Try starting the quiz again.", 
                               reply_markup=get_back_to_menu_keyboard())
            await state.clear()
            return
            
        logger.info(f"quiz.handle_answer: Found question with id={question_id}, quiz_id={question.quiz_id}")
        logger.info(f"quiz.handle_answer: Evaluating answer for question_id={question_id}, text='{question.question_text[:50]}...'")
        
        try:
            evaluation = await evaluate_answer(question.question_text, user_answer_text)
            logger.info(f"quiz.handle_answer: Successfully evaluated answer, is_correct={evaluation.get('is_correct')}")
        except Exception as eval_error:
            logger.error(f"quiz.handle_answer: Error evaluating answer: {eval_error}")
            logger.error(f"quiz.handle_answer: Stack trace for evaluation error:\n{traceback.format_exc()}")
            evaluation = {
                "is_correct": False,
                "score": 0,
                "feedback": "An error occurred while evaluating the answer. Please continue the quiz."
            }

        # Update answer with evaluation results
        logger.info(f"quiz.handle_answer: Updating user answer id={user_answer.id} with evaluation results")
        await crud.update_user_answer(session, user_answer.id, {
            "is_correct": evaluation.get("is_correct"),
            "score": evaluation.get("score", 0),
            "feedback": evaluation.get("feedback")
        })
        logger.info(f"quiz.handle_answer: Successfully updated user answer with evaluation results")

        logger.info(f"quiz.handle_answer: Sending evaluation feedback to telegram_id={telegram_id}")
        await message.answer(f"*Your answer has been evaluated:*\n\n{evaluation.get('feedback', 'No feedback.')}", parse_mode="Markdown")

        # Check for next question
        quiz_id = question.quiz_id
        logger.info(f"quiz.handle_answer: Getting all questions for quiz_id={quiz_id}")
        questions = await crud.get_questions_for_quiz(session, quiz_id)
        logger.info(f"quiz.handle_answer: Found {len(questions)} questions for quiz_id={quiz_id}")
        
        current_question_index = next((i for i, q in enumerate(questions) if q.id == question_id), None)
        logger.info(f"quiz.handle_answer: Current question index is {current_question_index} of {len(questions)-1}")

        if current_question_index is not None and current_question_index + 1 < len(questions):
            next_question = questions[current_question_index + 1]
            logger.info(f"quiz.handle_answer: Moving to next question id={next_question.id}, order={next_question.order}")
            await _show_question(message, state, session, next_question)
        else:
            # Quiz finished
            logger.info(f"quiz.handle_answer: Quiz completed for telegram_id={telegram_id}, calculating total score")
            
            # Calculate and save the total score
            total_score = await crud.calculate_and_save_total_score(session, attempt_id)
            
            logger.info(f"quiz.handle_answer: Total score for attempt_id={attempt_id} is {total_score}")
            
            await state.clear()
            logger.info(f"quiz.handle_answer: State cleared for telegram_id={telegram_id}")
            
            await message.answer(
                f"🎉 *Congratulations! You have completed the quiz.*\n\nYour total score: *{total_score}*",
                reply_markup=get_back_to_menu_keyboard(),
                parse_mode="Markdown"
            )
            logger.info(f"quiz.handle_answer: Successfully completed quiz for telegram_id={telegram_id}")
    except Exception as e:
        logger.error(f"quiz.handle_answer: Error processing answer for telegram_id={telegram_id}: {e}")
        # Log stack trace for debugging
        logger.error(f"quiz.handle_answer: Stack trace for answer error:\n{traceback.format_exc()}")
        
        # Try to send error message and reset state
        try:
            await message.answer("An error occurred while processing your answer. Try starting the quiz again.", 
                               reply_markup=get_back_to_menu_keyboard())
            await state.clear()
        except Exception as answer_error:
            logger.error(f"quiz.handle_answer: Failed to send error message: {answer_error}")
