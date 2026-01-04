from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from typing import List, Dict, Any
from loguru import logger


class MenuCallback(CallbackData, prefix="menu"):
    action: str

class TextLessonCallback(CallbackData, prefix="text_lesson"):
    action: str
    id: int

class ImageLessonCallback(CallbackData, prefix="image_lesson"):
    action: str
    id: int

class LessonCallback(CallbackData, prefix="lesson"):
    action: str
    id: int


class LessonStepCallback(CallbackData, prefix="lesson_step"):
    action: str
    lesson_id: int
    step_number: int


class QuizCallback(CallbackData, prefix="quiz"):
    action: str
    id: int

class QuizActionCallback(CallbackData, prefix="quiz_action"):
    action: str

class AdminCallback(CallbackData, prefix="admin"):
    action: str
    user_id: int | None = None

class PromptEvaluationCallback(CallbackData, prefix="prompt_eval"):
    action: str
    prompt_type: str  # 'text' or 'image'


# Main menu keyboard
def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📚 Text Prompt Lessons", callback_data=MenuCallback(action="text_lessons").pack()),
        InlineKeyboardButton(text="🖼 Image Prompt Lessons", callback_data=MenuCallback(action="image_lessons").pack())
    )
    builder.row(
        InlineKeyboardButton(text="📝 Quiz", callback_data=MenuCallback(action="quiz").pack()),
        InlineKeyboardButton(text="🔄 Generate", callback_data=MenuCallback(action="generate").pack())
    )
    builder.row(
        InlineKeyboardButton(text="📊 My Progress", callback_data=MenuCallback(action="progress").pack()),
        InlineKeyboardButton(text="🏆 Leaderboard", callback_data=MenuCallback(action="rating").pack()),
        InlineKeyboardButton(text="ℹ️ Help", callback_data=MenuCallback(action="help").pack())
    )
    if is_admin:
        admin_callback = AdminCallback(action="menu")
        builder.row(
            InlineKeyboardButton(text="👑 Admin Panel", callback_data=admin_callback.pack())
        )
    return builder.as_markup()


# Admin menu keyboard
def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Admin menu keyboard"""
    builder = InlineKeyboardBuilder()

    # Log the callback data being generated
    add_user_callback = AdminCallback(action="add_user")
    remove_user_callback = AdminCallback(action="remove_user")
    list_users_callback = AdminCallback(action="list_users")

    # Removed debug logging to avoid logger issues

    builder.row(
        InlineKeyboardButton(text="➕ Add User", callback_data=add_user_callback.pack()),
        InlineKeyboardButton(text="➖ Remove User", callback_data=remove_user_callback.pack())
    )
    builder.row(
        InlineKeyboardButton(text="👥 User List", callback_data=list_users_callback.pack())
    )
    return builder.as_markup()


# Lesson type selection keyboard
def get_lesson_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting lesson type"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📝 Text Prompts", callback_data=MenuCallback(action="text_lessons").pack()),
        InlineKeyboardButton(text="🎨 Image Prompts", callback_data=MenuCallback(action="image_lessons").pack())
    )
    builder.adjust(1)
    return builder.as_markup()


# Generation type selection keyboard
def get_generation_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting generation type"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📝 Generate Text", callback_data=MenuCallback(action="generate_text").pack()),
        InlineKeyboardButton(text="🎨 Generate Image", callback_data=MenuCallback(action="generate_image").pack())
    )
    builder.adjust(1)
    return builder.as_markup()


# Lessons list keyboard
def get_lessons_keyboard(lessons: List[Dict[str, Any]], lesson_type: str) -> InlineKeyboardMarkup:
    """Keyboard with available lessons"""
    builder = InlineKeyboardBuilder()
    Callback = TextLessonCallback if lesson_type == "text" else ImageLessonCallback

    for lesson in lessons:
        # Add completion status emoji
        status_emoji = "✅ " if lesson.get("completed") else "🔸 "
        builder.add(InlineKeyboardButton(
            text=f"{status_emoji}{lesson['title']}",
            callback_data=Callback(action="show", id=lesson['id']).pack()
        ))

    # Add back button
    builder.add(InlineKeyboardButton(text="🏠 Main Menu", callback_data=MenuCallback(action="main_menu").pack()))

    builder.adjust(1)
    return builder.as_markup()


# Lesson step navigation keyboard
def get_lesson_step_navigation_keyboard(lesson_id: int, current_step_number: int, total_steps: int, lesson_type: str) -> InlineKeyboardMarkup:
    """Keyboard for lesson step navigation"""
    builder = InlineKeyboardBuilder()
    Callback = TextLessonCallback if lesson_type == "text" else ImageLessonCallback

    if current_step_number < total_steps:
        builder.add(InlineKeyboardButton(
            text="➡️ Next Step",
            callback_data=LessonStepCallback(action="next", lesson_id=lesson_id, step_number=current_step_number).pack()
        ))
    else:
        builder.add(InlineKeyboardButton(
            text="✅ Complete Lesson",
            callback_data=Callback(action="finish", id=lesson_id).pack()
        ))

    action = "text_lessons" if lesson_type == "text" else "image_lessons"
    builder.add(InlineKeyboardButton(text="⬅️ Back to Lessons", callback_data=MenuCallback(action=action).pack()))

    # Add step counter
    builder.row(InlineKeyboardButton(text=f"Step {current_step_number}/{total_steps}", callback_data="ignore"))

    builder.adjust(1)
    return builder.as_markup()


# Lesson navigation keyboard
def get_lesson_practice_keyboard(lesson_id: int, lesson_type: str) -> InlineKeyboardMarkup:
    """Keyboard for lesson navigation"""
    builder = InlineKeyboardBuilder()
    Callback = TextLessonCallback if lesson_type == "text" else ImageLessonCallback
    
    # Add practice button
    builder.add(InlineKeyboardButton(
        text="✏️ Practice",
        callback_data=Callback(action="practice", id=lesson_id).pack()
    ))
    
    action = "text_lessons" if lesson_type == "text" else "image_lessons"
    builder.add(InlineKeyboardButton(text="⬅️ Back to List", callback_data=MenuCallback(action=action).pack()))
    
    builder.adjust(1)
    return builder.as_markup()


# Prompt evaluation keyboard
def get_evaluation_keyboard(lesson_id: int, lesson_type: str) -> InlineKeyboardMarkup:
    """Keyboard for prompt evaluation"""
    builder = InlineKeyboardBuilder()
    Callback = TextLessonCallback if lesson_type == "text" else ImageLessonCallback
    
    builder.add(
        InlineKeyboardButton(text="🔄 Try Again", callback_data=Callback(action="retry_practice", id=lesson_id).pack()),
        InlineKeyboardButton(text="✅ Complete Lesson", callback_data=Callback(action="complete", id=lesson_id).pack()),
        InlineKeyboardButton(text="⬅️ Back to Lesson", callback_data=Callback(action="show", id=lesson_id).pack())
    )
    
    builder.adjust(1)
    return builder.as_markup()


# Generation result keyboard
def get_generation_result_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for generation result"""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(text="🔄 Generate Again", callback_data=MenuCallback(action="generate_again").pack()),
        InlineKeyboardButton(text="📋 New Prompt", callback_data=MenuCallback(action="new_prompt").pack()),
        InlineKeyboardButton(text="🏠 Main Menu", callback_data=MenuCallback(action="main_menu").pack())
    )
    
    builder.adjust(1)
    return builder.as_markup()


# Cancel keyboard
def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Simple cancel keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Cancel", callback_data=MenuCallback(action="cancel").pack()))
    return builder.as_markup()


# Back to menu keyboard
def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Back to menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🏠 Back to Menu", callback_data=MenuCallback(action="main_menu").pack()))
    return builder.as_markup()


def get_quizzes_keyboard(quizzes: List[Any]) -> InlineKeyboardMarkup:
    """Keyboard with available quizzes."""
    builder = InlineKeyboardBuilder()
    for quiz in quizzes:
        builder.add(InlineKeyboardButton(
            text=f"📝 {quiz.title}",
            callback_data=QuizCallback(action="start", id=quiz.id).pack()
        ))
    builder.add(InlineKeyboardButton(text="🏠 Main Menu", callback_data=MenuCallback(action="main_menu").pack()))
    builder.adjust(1)
    return builder.as_markup()


def get_quiz_question_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for a quiz question, allowing user to cancel."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ End Quiz", callback_data=QuizActionCallback(action="cancel").pack()))
    return builder.as_markup()


def get_prompt_evaluation_keyboard(prompt_type: str) -> InlineKeyboardMarkup:
    """Keyboard for prompt evaluation choices"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Generate with current prompt", 
                           callback_data=PromptEvaluationCallback(action="proceed", prompt_type=prompt_type).pack())
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Improve prompt", 
                           callback_data=PromptEvaluationCallback(action="improve", prompt_type=prompt_type).pack())
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancel", 
                           callback_data=MenuCallback(action="main_menu").pack())
    )
    
    return builder.as_markup()
