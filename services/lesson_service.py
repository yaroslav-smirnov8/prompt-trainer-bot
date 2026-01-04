from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from database.models import Lesson, PromptExample, UserProgress
from services.ai_service import ai_service


class LessonService:
    """Service for managing lessons and user progress"""
    
    @staticmethod
    async def get_available_lessons(session: AsyncSession, user_id: int, lesson_type: str) -> List[Dict[str, Any]]:
        """Get available lessons for user with progress information"""
        # Get all lessons of specified type
        lessons = await crud.get_lessons_by_type(session, lesson_type)
        
        # Get user progress
        progress_list = await crud.get_user_progress(session, user_id)
        progress_map = {p.lesson_id: p for p in progress_list}
        
        result = []
        for lesson in lessons:
            progress = progress_map.get(lesson.id)
            lesson_data = {
                "id": lesson.id,
                "title": lesson.title,
                "description": lesson.description,
                "type": lesson.lesson_type,
                "order": lesson.order,
                "completed": progress.completed if progress else False,
                "score": progress.score if progress else None
            }
            result.append(lesson_data)
        
        return result
    
    @staticmethod
    async def get_lesson_with_examples(session: AsyncSession, lesson_id: int) -> Optional[Dict[str, Any]]:
        """Get lesson with its examples"""
        lesson = await crud.get_lesson(session, lesson_id)
        if not lesson:
            return None
        
        examples = await crud.get_examples_by_lesson(session, lesson_id)
        
        return {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "content": lesson.content,
            "type": lesson.lesson_type,
            "order": lesson.order,
            "examples": [
                {
                    "id": ex.id,
                    "prompt": ex.prompt_text,
                    "preview": ex.result_preview,
                    "type": ex.prompt_type
                } for ex in examples
            ]
        }
    
    @staticmethod
    async def mark_lesson_completed(session: AsyncSession, user_id: int, lesson_id: int, score: Optional[float] = None) -> bool:
        """Mark lesson as completed for user"""
        try:
            progress = await crud.get_or_create_progress(session, user_id, lesson_id)
            
            await crud.update_progress(session, progress.id, {
                "completed": True,
                "score": score,
                "completed_at": datetime.utcnow()
            })
            
            return True
        except Exception as e:
            print(f"Error marking lesson as completed: {e}")
            return False
    
    @staticmethod
    async def evaluate_prompt(prompt: str, prompt_type: str, lesson_id: Optional[int] = None) -> Tuple[bool, float, str]:
        """Evaluate user's prompt and return score and feedback"""
        # This is a simplified evaluation logic
        # In a real application, you might want to use more sophisticated evaluation
        
        # Basic criteria for evaluation
        criteria = {
            "text": [
                "clarity",
                "specificity",
                "context",
                "structure"
            ],
            "image": [
                "subject",
                "style",
                "composition",
                "details"
            ]
        }
        
        # Simple scoring based on prompt length and keywords
        score = 0.0
        feedback = ""
        
        # Check prompt length
        if len(prompt) < 10:
            feedback = "Prompt is too short. Add more details."
            return False, score, feedback
        
        # Basic scoring
        words = prompt.lower().split()
        unique_words = set(words)
        
        # Score based on length and vocabulary
        length_score = min(len(prompt) / 200, 1.0) * 0.3  # 30% of score based on length (up to 200 chars)
        vocab_score = min(len(unique_words) / 30, 1.0) * 0.3  # 30% of score based on vocabulary
        
        score = length_score + vocab_score
        
        # Check for criteria keywords in the prompt
        criteria_score = 0.0
        criteria_feedback = []
        
        for criterion in criteria.get(prompt_type, []):
            if any(keyword in prompt.lower() for keyword in [criterion, criterion + "s", criterion + "ed", criterion + "ing"]):
                criteria_score += 0.1  # 10% per criterion (max 40%)
                criteria_feedback.append(f"✓ Well described aspect '{criterion}'")
            else:
                criteria_feedback.append(f"✗ It is recommended to add description of aspect '{criterion}'")
        
        score += criteria_score
        score = min(score, 1.0)  # Cap at 1.0 (100%)
        
        # Generate feedback
        if score < 0.3:
            feedback = "Your prompt needs significant improvement. " + "\n".join(criteria_feedback)
        elif score < 0.6:
            feedback = "Your prompt is decent, but there's room for improvement. " + "\n".join(criteria_feedback)
        else:
            feedback = "Excellent prompt! " + "\n".join(criteria_feedback)
        
        return True, score, feedback
    
    @staticmethod
    async def generate_from_prompt(prompt: str, prompt_type: str) -> Tuple[bool, str]:
        """Generate result from user's prompt using AI service"""
        if prompt_type == "text":
            success, result = await ai_service.generate_text(prompt)
        else:  # image
            success, result = await ai_service.generate_image(prompt)
        
        return success, result
    
    @staticmethod
    async def save_generated_prompt(session: AsyncSession, user_id: int, prompt: str, 
                                   prompt_type: str, result: str) -> bool:
        """Save generated prompt to database"""
        try:
            await crud.create_generated_prompt(session, user_id, prompt, prompt_type, result)
            return True
        except Exception as e:
            print(f"Error saving generated prompt: {e}")
            return False
    
    @staticmethod
    async def get_user_progress_summary(session: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Get summary of user's progress"""
        progress_list = await crud.get_user_progress(session, user_id)
        
        total_lessons = len(progress_list)
        completed_lessons = sum(1 for p in progress_list if p.completed)
        avg_score = sum(p.score or 0 for p in progress_list if p.completed) / max(completed_lessons, 1)
        
        # Get counts by lesson type
        text_lessons = await crud.get_lessons_by_type(session, "text")
        image_lessons = await crud.get_lessons_by_type(session, "image")
        
        text_completed = 0
        image_completed = 0
        
        for p in progress_list:
            if p.completed:
                lesson = await crud.get_lesson(session, p.lesson_id)
                if lesson.lesson_type == "text":
                    text_completed += 1
                elif lesson.lesson_type == "image":
                    image_completed += 1
        
        return {
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "completion_percentage": (completed_lessons / max(total_lessons, 1)) * 100,
            "average_score": avg_score,
            "text_lessons": {
                "total": len(text_lessons),
                "completed": text_completed,
                "percentage": (text_completed / max(len(text_lessons), 1)) * 100
            },
            "image_lessons": {
                "total": len(image_lessons),
                "completed": image_completed,
                "percentage": (image_completed / max(len(image_lessons), 1)) * 100
            }
        }


# Create singleton instance
lesson_service = LessonService()
