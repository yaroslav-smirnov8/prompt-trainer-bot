from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any, Union

from database.models import (User, Lesson, LessonStep, PromptExample, UserProgress, 
                         GeneratedPrompt, Quiz, Question, QuizAttempt, UserAnswer)


# User CRUD operations
async def create_user(session: AsyncSession, user_id: int, username: Optional[str] = None, full_name: Optional[str] = None) -> User:
    """Create a new user"""
    import logging
    import inspect
    import traceback
    
    # Get caller function information
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    
    logging.info(f"create_user called with user_id={user_id}, username={username}, full_name={full_name} from {caller_info}")
    
    # Check for suspicious ID
    if user_id == 1:
        logging.critical(f"SUSPICIOUS: Attempt to create user with user_id=1 from {caller_info}")
        stack_trace = ''.join(traceback.format_stack())
        logging.critical(f"Stack trace for user_id=1 creation attempt:\n{stack_trace}")
        
        # Check if user with this ID already exists
        existing_user_result = await session.execute(select(User).where(User.user_id == user_id))
        existing_user = existing_user_result.scalars().first()
        if existing_user:
            logging.warning(f"User with user_id=1 already exists with database id={existing_user.id}")
            return existing_user
    
    # Check if user with this telegram_id already exists
    existing_user_result = await session.execute(select(User).where(User.user_id == user_id))
    existing_user = existing_user_result.scalars().first()
    if existing_user:
        logging.warning(f"User with user_id={user_id} already exists with database id={existing_user.id}, returning existing user")
        return existing_user
    
    try:
        # Create new user
        user = User(user_id=user_id, username=username, full_name=full_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        logging.info(f"Successfully created new user with database id={user.id} for user_id={user_id}")
        
        # Log all users in database for debugging
        if user_id == 1:
            all_users_result = await session.execute(select(User))
            all_users = all_users_result.scalars().all()
            logging.info(f"All users in database after creating user_id=1: {[(u.id, u.user_id) for u in all_users]}")
        
        return user
    except Exception as e:
        logging.error(f"Error creating user with user_id={user_id}: {e}")
        logging.error(f"Stack trace for user creation error:\n{traceback.format_exc()}")
        raise


async def get_user_safe(session: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by Telegram ID without raising an exception if not found"""
    import inspect
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    # Get the caller's information
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    
    logger.info(f"get_user_safe called with user_id={user_id} from {caller_info}")
    
    # Log the full call stack to trace where this is being called from
    if user_id == 1:
        stack_trace = ''.join(traceback.format_stack())
        logger.warning(f"SUSPICIOUS: get_user_safe called with user_id=1, full stack trace:\n{stack_trace}")
    
    try:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalars().first()
        if not user:
            logger.warning(f"User with Telegram ID {user_id} not found (safe method), called from {caller_info}")
            # Log all users in the database to check if there's a mismatch
            if user_id == 1:
                all_users_result = await session.execute(select(User))
                all_users = all_users_result.scalars().all()
                logger.warning(f"All users in database: {[(u.id, u.user_id) for u in all_users]}")
        else:
            logger.info(f"User found: id={user.id}, user_id={user.user_id}, username={user.username}")
        return user
    except Exception as e:
        logger.error(f"Error in get_user_safe: {e}")
        return None


async def get_user(session: AsyncSession, user_id: int) -> User:
    """Get user by Telegram ID, raises ValueError if user not found"""
    import inspect
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    # Get the caller's information
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    
    logger.info(f"get_user called with user_id={user_id} from {caller_info}")
    
    # Check for suspicious ID
    if user_id == 1:
        logger.critical(f"SUSPICIOUS: get_user called with user_id=1 from {caller_info}")
        stack_trace = ''.join(traceback.format_stack())
        logger.critical(f"Stack trace for user_id=1 request:\n{stack_trace}")
    
    user = await get_user_safe(session, user_id)
    if user is None:
        logger.error(f"User with Telegram ID {user_id} not found, called from {caller_info}")
        raise ValueError(f"User with Telegram ID {user_id} not found. Please use /start to register.")
    return user


async def update_user(session: AsyncSession, user_id: int, data: Dict[str, Any]) -> Optional[User]:
    """Update user data"""
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(**data)
    )
    await session.commit()
    return await get_user(session, user_id)


async def set_admin_status(session: AsyncSession, user_id: int, is_admin: bool = True) -> Optional[User]:
    """Set user admin status"""
    return await update_user(session, user_id, {"is_admin": is_admin})


async def get_all_users(session: AsyncSession) -> List[User]:
    """Get all users"""
    result = await session.execute(select(User))
    return result.scalars().all()


async def activate_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Activate a user"""
    return await update_user(session, user_id, {"is_active": True})


async def deactivate_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Deactivate a user"""
    return await update_user(session, user_id, {"is_active": False})


# Lesson CRUD operations
async def create_lesson(session: AsyncSession, title: str, lesson_type: str, 
                       order: int, description: Optional[str] = None) -> Lesson:
    """Create a new lesson"""
    lesson = Lesson(
        title=title,
        description=description,
        lesson_type=lesson_type,
        order=order,
        is_active=True
    )
    session.add(lesson)
    await session.commit()
    await session.refresh(lesson)
    return lesson


from sqlalchemy.orm import selectinload

async def get_lesson_by_id(session: AsyncSession, lesson_id: int) -> Optional[Lesson]:
    """Get lesson by ID"""
    result = await session.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.steps))
    )
    return result.scalars().first()


async def update_lesson(session: AsyncSession, lesson_id: int, data: Dict[str, Any]) -> Optional[Lesson]:
    """Update lesson data"""
    await session.execute(
        update(Lesson)
        .where(Lesson.id == lesson_id)
        .values(**data)
    )
    await session.commit()
    return await get_lesson_by_id(session, lesson_id)


async def get_lesson_by_title(session: AsyncSession, title: str) -> Optional[Lesson]:
    """Get lesson by title"""
    result = await session.execute(select(Lesson).where(Lesson.title == title))
    return result.scalars().first()


async def get_lessons_by_type(session: AsyncSession, lesson_type: str, active_only: bool = True) -> List[Lesson]:
    """Get all lessons of specific type"""
    query = select(Lesson).where(Lesson.lesson_type == lesson_type)
    if active_only:
        query = query.where(Lesson.is_active == True)
    query = query.order_by(Lesson.order)
    result = await session.execute(query)
    return result.scalars().all()


async def is_lesson_completed(session: AsyncSession, user_id: int, lesson_id: int) -> bool:
    """Check if a user has completed all steps in a lesson."""
    import logging
    import traceback
    
    logging.info(f"is_lesson_completed: Checking completion status for user_id={user_id}, lesson_id={lesson_id}")
    
    # Check for suspicious ID
    if user_id == 1:
        logging.critical(f"is_lesson_completed: SUSPICIOUS - Request for lesson completion check with user_id=1! Lesson ID: {lesson_id}")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logging.critical(f"is_lesson_completed: Stack trace for user_id=1 detection:\n{stack_trace}")
    
    try:
        logging.info(f"is_lesson_completed: Getting lesson steps for lesson_id={lesson_id}")
        all_steps = await get_lesson_steps(session, lesson_id)
        
        if not all_steps:
            # If there are no steps, the lesson is considered not completed by default
            logging.info(f"is_lesson_completed: No steps found for lesson_id={lesson_id}, returning False")
            return False
        
        logging.info(f"is_lesson_completed: Found {len(all_steps)} steps for lesson_id={lesson_id}")
        
        logging.info(f"is_lesson_completed: Getting user progress for user_id={user_id}, lesson_id={lesson_id}")
        user_progress = await get_user_progress_for_lesson(session, user_id, lesson_id)
        
        if not user_progress and user_id == 1:
            logging.critical(f"is_lesson_completed: No progress found for user_id=1, lesson_id={lesson_id}")
        
        completed_steps_count = sum(1 for p in user_progress if p.completed)
        logging.info(f"is_lesson_completed: User_id={user_id} has completed {completed_steps_count}/{len(all_steps)} steps for lesson_id={lesson_id}")
        
        is_completed = len(all_steps) == completed_steps_count
        logging.info(f"is_lesson_completed: Lesson completion status for user_id={user_id}, lesson_id={lesson_id}: {is_completed}")
        
        return is_completed
    except Exception as e:
        logging.error(f"is_lesson_completed: Error checking lesson completion for user_id={user_id}, lesson_id={lesson_id}: {e}")
        logging.error(f"is_lesson_completed: Stack trace:\n{traceback.format_exc()}")
        # In case of error consider lesson incomplete
        return False


# PromptExample CRUD operations
async def create_prompt_example(session: AsyncSession, lesson_id: int, prompt_text: str, 
                               prompt_type: str, result_preview: Optional[str] = None) -> PromptExample:
    """Create a new prompt example"""
    example = PromptExample(
        lesson_id=lesson_id,
        prompt_text=prompt_text,
        result_preview=result_preview,
        prompt_type=prompt_type
    )
    session.add(example)
    await session.commit()
    await session.refresh(example)
    return example


async def get_examples_by_lesson(session: AsyncSession, lesson_id: int) -> List[PromptExample]:
    """Get all examples for a specific lesson"""
    result = await session.execute(
        select(PromptExample).where(PromptExample.lesson_id == lesson_id)
    )
    return result.scalars().all()


# LessonStep CRUD operations
async def create_lesson_step(session: AsyncSession, lesson_id: int, step_number: int, content: str) -> LessonStep:
    """Create a new lesson step"""
    step = LessonStep(
        lesson_id=lesson_id,
        step_number=step_number,
        content=content
    )
    session.add(step)
    await session.commit()
    await session.refresh(step)
    return step


async def get_lesson_step_by_number(session: AsyncSession, lesson_id: int, step_number: int) -> Optional[LessonStep]:
    """Get a specific lesson step by its number and lesson ID."""
    result = await session.execute(
        select(LessonStep).where(
            LessonStep.lesson_id == lesson_id,
            LessonStep.step_number == step_number
        )
    )
    return result.scalars().first()


async def delete_lesson_steps(session: AsyncSession, lesson_id: int):
    """Delete all steps for a specific lesson"""
    await session.execute(
        delete(LessonStep).where(LessonStep.lesson_id == lesson_id)
    )
    await session.commit()


async def get_lesson_steps(session: AsyncSession, lesson_id: int) -> List[LessonStep]:
    """Get all steps for a specific lesson"""
    result = await session.execute(
        select(LessonStep)
        .where(LessonStep.lesson_id == lesson_id)
        .order_by(LessonStep.step_number)
    )
    return result.scalars().all()


# UserProgress CRUD operations
async def get_or_create_progress(session: AsyncSession, user_id: int, lesson_step_id: int) -> UserProgress:
    """Get or create user progress for a lesson"""
    import logging
    import traceback
    
    logging.info(f"get_or_create_progress: Processing for user_id={user_id}, lesson_step_id={lesson_step_id}")
    
    # Check for suspicious ID
    if user_id == 1:
        logging.critical(f"get_or_create_progress: SUSPICIOUS - Request for progress with user_id=1! Lesson step ID: {lesson_step_id}")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logging.critical(f"get_or_create_progress: Stack trace for user_id=1 detection:\n{stack_trace}")
    
    try:
        # First get the user's database ID
        logging.info(f"get_or_create_progress: Getting user from database for user_id={user_id}")
        user_result = await session.execute(select(User).where(User.user_id == user_id))
        user = user_result.scalars().first()
        
        if not user:
            error_msg = f"User with Telegram ID {user_id} not found"
            logging.error(f"get_or_create_progress: {error_msg}")
            raise ValueError(error_msg)
        
        logging.info(f"get_or_create_progress: Found user with database id={user.id} for user_id={user_id}")
        
        # Check if progress exists
        logging.info(f"get_or_create_progress: Checking if progress exists for user_id={user_id}, db_id={user.id}, lesson_step_id={lesson_step_id}")
        result = await session.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.lesson_step_id == lesson_step_id
            )
        )
        progress = result.scalars().first()
        
        if not progress:
            # Create new progress
            logging.info(f"get_or_create_progress: Creating new progress for user_id={user_id}, db_id={user.id}, lesson_step_id={lesson_step_id}")
            progress = UserProgress(user_id=user.id, lesson_step_id=lesson_step_id)
            session.add(progress)
            await session.commit()
            await session.refresh(progress)
            logging.info(f"get_or_create_progress: Created new progress with id={progress.id}")
        else:
            logging.info(f"get_or_create_progress: Found existing progress with id={progress.id}, completed={progress.completed}")
        
        return progress
    except Exception as e:
        logging.error(f"get_or_create_progress: Error processing progress for user_id={user_id}, lesson_step_id={lesson_step_id}: {e}")
        logging.error(f"get_or_create_progress: Stack trace:\n{traceback.format_exc()}")
        raise


async def update_progress(session: AsyncSession, progress_id: int, 
                          data: Dict[str, Any]) -> Optional[UserProgress]:
    """Update user progress"""
    await session.execute(
        update(UserProgress)
        .where(UserProgress.id == progress_id)
        .values(**data)
    )
    await session.commit()
    
    result = await session.execute(select(UserProgress).where(UserProgress.id == progress_id))
    return result.scalars().first()


async def get_user_progress_for_lesson(session: AsyncSession, user_id: int, lesson_id: int) -> List[UserProgress]:
    """Get user progress for a specific lesson"""
    import logging
    import traceback
    
    logging.info(f"get_user_progress_for_lesson (second implementation): Getting progress for user_id={user_id}, lesson_id={lesson_id}")
    
    # Check for suspicious ID
    if user_id == 1:
        logging.critical(f"get_user_progress_for_lesson (second implementation): SUSPICIOUS - Request for progress with user_id=1! Lesson ID: {lesson_id}")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logging.critical(f"get_user_progress_for_lesson (second implementation): Stack trace for user_id=1 detection:\n{stack_trace}")
    
    try:
        logging.info(f"get_user_progress_for_lesson (second implementation): Querying user with user_id={user_id}")
        user_result = await session.execute(select(User).where(User.user_id == user_id))
        user = user_result.scalars().first()
        
        if not user:
            logging.warning(f"get_user_progress_for_lesson (second implementation): User with user_id={user_id} not found in database")
            return []
        
        logging.info(f"get_user_progress_for_lesson (second implementation): Found user with database id={user.id} for user_id={user_id}")
        
        logging.info(f"get_user_progress_for_lesson (second implementation): Querying progress for user_id={user_id}, db_id={user.id}, lesson_id={lesson_id}")
        result = await session.execute(
            select(UserProgress)
            .join(LessonStep)
            .where(UserProgress.user_id == user.id, LessonStep.lesson_id == lesson_id)
        )
        
        progress_list = result.scalars().all()
        logging.info(f"get_user_progress_for_lesson (second implementation): Found {len(progress_list)} progress records for user_id={user_id}, lesson_id={lesson_id}")
        
        return progress_list
    except Exception as e:
        logging.error(f"get_user_progress_for_lesson (second implementation): Error getting progress for user_id={user_id}, lesson_id={lesson_id}: {e}")
        logging.error(f"get_user_progress_for_lesson (second implementation): Stack trace:\n{traceback.format_exc()}")
        return []


async def get_user_progress(session: AsyncSession, user_id: int) -> List[UserProgress]:
    """Get all progress for a user"""
    # First get the user's database ID
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()
    
    if not user:
        return []
        
    result = await session.execute(
        select(UserProgress).where(UserProgress.user_id == user.id)
    )
    return result.scalars().all()


# Quiz CRUD operations
async def create_quiz(session: AsyncSession, title: str, description: Optional[str] = None, lesson_id: Optional[int] = None) -> Quiz:
    """Create a new quiz"""
    quiz = Quiz(title=title, description=description, lesson_id=lesson_id)
    session.add(quiz)
    await session.commit()
    await session.refresh(quiz)
    return quiz


async def get_quiz_by_id(session: AsyncSession, quiz_id: int) -> Optional[Quiz]:
    """Get quiz by ID"""
    result = await session.execute(select(Quiz).where(Quiz.id == quiz_id))
    return result.scalars().first()


async def get_quiz_by_title(session: AsyncSession, title: str) -> Optional[Quiz]:
    """Get quiz by title"""
    result = await session.execute(select(Quiz).where(Quiz.title == title))
    return result.scalars().first()


async def get_quizzes(session: AsyncSession) -> List[Quiz]:
    """Get all quizzes"""
    result = await session.execute(select(Quiz).order_by(Quiz.id))
    return result.scalars().all()


# Question CRUD operations
async def create_question(session: AsyncSession, quiz_id: int, question_text: str, order: int) -> Question:
    """Create a new question"""
    question = Question(quiz_id=quiz_id, question_text=question_text, order=order)
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question


async def get_questions_for_quiz(session: AsyncSession, quiz_id: int) -> List[Question]:
    """Get all questions for a specific quiz"""
    import logging
    import inspect
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    logging.info(f"get_questions_for_quiz called with quiz_id={quiz_id} from {caller_info}")
    
    try:
        result = await session.execute(
            select(Question)
            .where(Question.quiz_id == quiz_id)
            .order_by(Question.order)
        )
        questions = result.scalars().all()
        logging.info(f"Found {len(questions)} questions for quiz_id={quiz_id}")
        return questions
    except Exception as e:
        logging.error(f"Error in get_questions_for_quiz: {e}")
        raise


async def get_question_by_id(session: AsyncSession, question_id: int) -> Optional[Question]:
    """Get question by ID"""
    import logging
    import inspect
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    logging.info(f"get_question_by_id called with question_id={question_id} from {caller_info}")
    
    try:
        result = await session.execute(select(Question).where(Question.id == question_id))
        question = result.scalars().first()
        if question:
            logging.info(f"Found question with id={question.id}, quiz_id={question.quiz_id}")
        else:
            logging.warning(f"Question with id={question_id} not found")
        return question
    except Exception as e:
        logging.error(f"Error in get_question_by_id: {e}")
        return None


# QuizAttempt CRUD operations
async def create_quiz_attempt(session: AsyncSession, user_id: int, quiz_id: int) -> QuizAttempt:
    """Create a new quiz attempt"""
    import logging
    import inspect
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    logging.info(f"create_quiz_attempt called with user_id={user_id}, quiz_id={quiz_id} from {caller_info}")
    
    user_db = await get_user(session, user_id)
    if not user_db:
        logging.error(f"User with ID {user_id} not found in create_quiz_attempt")
        raise ValueError(f"User with ID {user_id} not found")
    
    logging.info(f"Found user with database id={user_db.id} for telegram_id={user_id}")
    attempt = QuizAttempt(user_id=user_db.id, quiz_id=quiz_id)
    session.add(attempt)
    await session.commit()
    await session.refresh(attempt)
    return attempt


async def get_quiz_attempt(session: AsyncSession, attempt_id: int) -> Optional[QuizAttempt]:
    """Get a quiz attempt by its ID"""
    import logging
    import inspect
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    logging.info(f"get_quiz_attempt called with attempt_id={attempt_id} from {caller_info}")
    
    try:
        result = await session.execute(select(QuizAttempt).where(QuizAttempt.id == attempt_id))
        attempt = result.scalars().first()
        if attempt:
            logging.info(f"Found quiz attempt with id={attempt.id}, user_id={attempt.user_id}, quiz_id={attempt.quiz_id}")
        else:
            logging.warning(f"Quiz attempt with id={attempt_id} not found")
        return attempt
    except Exception as e:
        logging.error(f"Error in get_quiz_attempt: {e}")
        return None


async def update_quiz_attempt(session: AsyncSession, attempt_id: int, data: Dict[str, Any]) -> Optional[QuizAttempt]:
    """Update quiz attempt data"""
    await session.execute(
        update(QuizAttempt)
        .where(QuizAttempt.id == attempt_id)
        .values(**data)
    )
    await session.commit()
    return await get_quiz_attempt(session, attempt_id)


# UserAnswer CRUD operations
async def create_user_answer(session: AsyncSession, attempt_id: int, question_id: int, answer_text: str) -> UserAnswer:
    """Create a new user answer"""
    import logging
    import inspect
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    logging.info(f"create_user_answer called with attempt_id={attempt_id}, question_id={question_id} from {caller_info}")
    
    # Get attempt and user information
    attempt_result = await session.execute(select(QuizAttempt).where(QuizAttempt.id == attempt_id))
    attempt = attempt_result.scalars().first()
    if attempt:
        logging.info(f"Found attempt with user_id={attempt.user_id}")
    else:
        logging.warning(f"Attempt with id={attempt_id} not found")
    
    answer = UserAnswer(attempt_id=attempt_id, question_id=question_id, answer_text=answer_text)
    session.add(answer)
    await session.commit()
    await session.refresh(answer)
    return answer


# GeneratedPrompt CRUD operations
async def create_generated_prompt(session: AsyncSession, user_id: int, prompt_text: str, 
                                 prompt_type: str, result: Optional[str] = None) -> GeneratedPrompt:
    """Create a record of generated prompt"""
    # Add caller function information
    import inspect
    import logging
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    logging.info(f"create_generated_prompt called with user_id={user_id} from {caller_info}")
    
    # First get the user's database ID
    user_result = await session.execute(select(User).where(User.user_id == user_id))
    user = user_result.scalars().first()
    if not user:
        logging.error(f"User with Telegram ID {user_id} not found in create_generated_prompt")
        raise ValueError(f"User with Telegram ID {user_id} not found")
    
    generated = GeneratedPrompt(
        user_id=user.id,
        prompt_text=prompt_text,
        result=result,
        prompt_type=prompt_type
    )
    session.add(generated)
    await session.commit()
    await session.refresh(generated)
    return generated
async def update_user_answer(session: AsyncSession, answer_id: int, data: Dict[str, Any]) -> Optional[UserAnswer]:
    """Update user answer data"""
    import logging
    import inspect
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    logging.info(f"update_user_answer called with answer_id={answer_id}, data={data} from {caller_info}")
    
    try:
        # Get answer and user information
        answer_result = await session.execute(select(UserAnswer).where(UserAnswer.id == answer_id))
        answer = answer_result.scalars().first()
        if not answer:
            logging.warning(f"Answer with id={answer_id} not found")
            return None
            
        # Get attempt and user information
        attempt_result = await session.execute(select(QuizAttempt).where(QuizAttempt.id == answer.attempt_id))
        attempt = attempt_result.scalars().first()
        if attempt:
            logging.info(f"Found attempt with user_id={attempt.user_id} for answer_id={answer_id}")
        else:
            logging.warning(f"Attempt for answer_id={answer_id} not found")
        
        await session.execute(
            update(UserAnswer)
            .where(UserAnswer.id == answer_id)
            .values(**data)
        )
        await session.commit()
        result = await session.execute(select(UserAnswer).where(UserAnswer.id == answer_id))
        return result.scalars().first()
    except Exception as e:
        logging.error(f"Error in update_user_answer: {e}")
        return None


async def get_next_step_for_user(session: AsyncSession, user_id: int, lesson_id: int) -> Optional[LessonStep]:
    """Get the next uncompleted step for a user in a lesson."""
    import logging
    import traceback
    
    logging.info(f"get_next_step_for_user: Getting next step for user_id={user_id}, lesson_id={lesson_id}")
    
    # Check for suspicious ID
    if user_id == 1:
        logging.critical(f"get_next_step_for_user: SUSPICIOUS - Request for next step with user_id=1! Lesson ID: {lesson_id}")
        # Log additional debug information
        stack_trace = ''.join(traceback.format_stack())
        logging.critical(f"get_next_step_for_user: Stack trace for user_id=1 detection:\n{stack_trace}")
    
    try:
        logging.info(f"get_next_step_for_user: Getting user progress for user_id={user_id}, lesson_id={lesson_id}")
        user_progress = await get_user_progress_for_lesson(session, user_id, lesson_id)
        
        if not user_progress and user_id == 1:
            logging.critical(f"get_next_step_for_user: No progress found for user_id=1, lesson_id={lesson_id}")
        
        completed_step_ids = {p.lesson_step_id for p in user_progress if p.completed}
        logging.info(f"get_next_step_for_user: User_id={user_id} has completed {len(completed_step_ids)} steps for lesson_id={lesson_id}")
        
        logging.info(f"get_next_step_for_user: Getting all steps for lesson_id={lesson_id}")
        all_steps = await get_lesson_steps(session, lesson_id)
        logging.info(f"get_next_step_for_user: Found {len(all_steps)} total steps for lesson_id={lesson_id}")
        
        for step in all_steps:
            if step.id not in completed_step_ids:
                logging.info(f"get_next_step_for_user: Found next step id={step.id}, number={step.step_number} for user_id={user_id}, lesson_id={lesson_id}")
                return step
        
        logging.info(f"get_next_step_for_user: No uncompleted steps found for user_id={user_id}, lesson_id={lesson_id}")
        return None
    except Exception as e:
        logging.error(f"get_next_step_for_user: Error getting next step for user_id={user_id}, lesson_id={lesson_id}: {e}")
        logging.error(f"get_next_step_for_user: Stack trace:\n{traceback.format_exc()}")
        return None


# GeneratedPrompt CRUD operations
async def create_generated_prompt(session: AsyncSession, user_id: int, prompt_text: str, 
                                 prompt_type: str, result: Optional[str] = None) -> GeneratedPrompt:
    """Create a record of generated prompt"""
    # Add caller function information
    import inspect
    import logging
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    logging.info(f"create_generated_prompt called with user_id={user_id} from {caller_info}")
    
    # First get the user's database ID
    user_result = await session.execute(select(User).where(User.user_id == user_id))
    user = user_result.scalars().first()
    if not user:
        logging.error(f"User with Telegram ID {user_id} not found in create_generated_prompt")
        raise ValueError(f"User with Telegram ID {user_id} not found")
    
    generated = GeneratedPrompt(
        user_id=user.id,
        prompt_text=prompt_text,
        result=result,
        prompt_type=prompt_type
    )
    session.add(generated)
    await session.commit()
    await session.refresh(generated)
    return generated


async def calculate_and_save_total_score(session: AsyncSession, attempt_id: int) -> float:
    """Calculate and save the total score for a quiz attempt."""
    from sqlalchemy import func

    # Calculate the sum of scores for all answers in the attempt
    result = await session.execute(
        select(func.sum(UserAnswer.score))
        .where(UserAnswer.attempt_id == attempt_id)
    )
    total_score = result.scalar_one_or_none() or 0.0

    # Update the total_score in the QuizAttempt table
    await session.execute(
        update(QuizAttempt)
        .where(QuizAttempt.id == attempt_id)
        .values(total_score=total_score)
    )
    await session.commit()
    
    return total_score


async def get_user_generated_prompts(session: AsyncSession, user_id: int, 
                                    prompt_type: Optional[str] = None) -> List[GeneratedPrompt]:
    """Get all generated prompts for a user"""
    # First get the user's database ID
    user_result = await session.execute(select(User).where(User.user_id == user_id))
    user = user_result.scalars().first()
    if not user:
        return []
    
    query = select(GeneratedPrompt).where(GeneratedPrompt.user_id == user.id)
    if prompt_type:
        query = query.where(GeneratedPrompt.prompt_type == prompt_type)
    query = query.order_by(GeneratedPrompt.created_at.desc())
    
    result = await session.execute(query)
    return result.scalars().all()


async def get_user_ratings(session: AsyncSession, top_n: int = 10) -> List[Dict[str, Any]]:
    """Get user ratings based on their quiz scores."""
    from sqlalchemy import func

    result = await session.execute(
        select(
            User.username,
            User.full_name,
            func.sum(UserAnswer.score).label('total_score'),
            func.count(UserAnswer.id).label('answers_count')
        )
        .join(QuizAttempt, User.id == QuizAttempt.user_id)
        .join(UserAnswer, QuizAttempt.id == UserAnswer.attempt_id)
        .group_by(User.id, User.username, User.full_name)
        .order_by(func.sum(UserAnswer.score).desc())
        .limit(top_n)
    )
    
    ratings = [
        {
            "username": row.username,
            "full_name": row.full_name,
            "total_score": row.total_score,
            "answers_count": row.answers_count
        }
        for row in result.all()
    ]
    
    return ratings
