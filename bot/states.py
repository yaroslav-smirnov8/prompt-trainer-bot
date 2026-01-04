from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """States for the user"""
    menu = State()
    
    # Lesson states
    viewing_lessons = State()
    in_lesson = State()
    
    # Quiz states
    viewing_quizzes = State()
    in_quiz = State()

    # Generation states
    choosing_generation_type = State()
    entering_prompt = State()
    entering_image_prompt = State()
    
    # Prompt evaluation states
    reviewing_text_prompt = State()
    reviewing_image_prompt = State()
    editing_text_prompt = State()
    editing_image_prompt = State()
    
    generating = State()


class AdminStates(StatesGroup):
    """States for the admin"""
    menu = State()
    waiting_for_user_to_add = State()
    waiting_for_user_to_remove = State()
