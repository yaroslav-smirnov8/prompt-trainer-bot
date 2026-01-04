from sqlalchemy.ext.asyncio import AsyncSession

from bot.lessons_data import TEXT_LESSONS, IMAGE_LESSONS
from database import crud
from database.models import Quiz, Question


async def populate_quizzes(session: AsyncSession):
    """Populate the database with quizzes and questions."""
    quizzes_data = [
        {
            "title": "Prompt Engineering Basics Quiz",
            "description": "Test your knowledge of prompt creation fundamentals.",
            "lesson_id": 1,
            "questions": [
                {"question_text": "What is a prompt?", "order": 1},
                {"question_text": "Name 2 main types of prompts.", "order": 2},
                {"question_text": "Which component in a prompt sets its main goal?", "order": 3},
                {"question_text": "What is 'temperature' in the context of text generation?", "order": 4},
                {"question_text": "How can you improve detail in a model's response?", "order": 5},
                {"question_text": "What is 'few-shot' prompting?", "order": 6},
                {"question_text": "Which operator is used to specify word weight in a prompt?", "order": 7},
                {"question_text": "How to avoid bias in model responses?", "order": 8},
                {"question_text": "What is 'Chain of Thought' prompting?", "order": 9},
                {"question_text": "How to properly format a prompt to get code?", "order": 10},
            ]
        },
        {
            "title": "Image Generation Quiz",
            "description": "Test your knowledge of creating prompts for image generation.",
            "lesson_id": 1,
            "questions": [
                {"question_text": "Which parameter controls the aspect ratio of an image?", "order": 1},
                {"question_text": "What is a negative prompt?", "order": 2},
                {"question_text": "How can you specify image style in a prompt?", "order": 3},
                {"question_text": "What is 'seed' and what is it used for?", "order": 4},
                {"question_text": "How can you blend two images in a prompt?", "order": 5},
                {"question_text": "Which parameter affects the model's 'creativity' in image generation?", "order": 6},
                {"question_text": "How can you use an image as a reference?", "order": 7},
                {"question_text": "What are 'outpainting' and 'inpainting'?", "order": 8},
                {"question_text": "How can you animate a generated image?", "order": 9},
                {"question_text": "Which file format is best for saving generated images without quality loss?", "order": 10},
            ]
        },
        {
            "title": "Text Prompts for Teachers",
            "description": "Create a prompt for a language model.",
            "lesson_id": 2,
            "questions": [
                {"question_text": "Create a prompt to generate a dialogue between two friends discussing weekend plans. The dialogue should be in English, Intermediate level (B1), and contain at least 5 lines from each participant.", "order": 1},
            ]
        },
        {
            "title": "Image Prompts",
            "description": "Create a prompt for image generation.",
            "lesson_id": 3,
            "questions": [
                {"question_text": "Create a prompt to generate an image illustrating the idiom 'break a leg'. The image should be in cartoon style and show an actor on stage.", "order": 1},
            ]
        },
        {
            "title": "Creative Games for Lessons",
            "description": "Create a prompt to generate a language game idea.",
            "lesson_id": 4,
            "questions": [
                {"question_text": "Create a prompt to generate a 'Detective Agency' game where students must guess the 'criminal' (a word or grammatical construction) through leading questions.", "order": 1},
                {"question_text": "Come up with a prompt to create an auction game where lots are rare words, and students 'buy' them by composing sentences with these words.", "order": 2},
                {"question_text": "Create a prompt for a 'Linguistic Charades' game where you need to explain words or phrases using synonyms, antonyms, and descriptions without naming the word itself.", "order": 3},
                {"question_text": "Come up with a prompt to create a 'Time Travel' role-playing game where students find themselves in different eras and must use appropriate vocabulary.", "order": 4},
                {"question_text": "Create a prompt for a 'Poetry Battle' game where students compete in writing short poems on a given topic using a specific set of words.", "order": 5},
                {"question_text": "Come up with a prompt to create a 'Cooking Show' game where students must 'cook' a dish, describing the process and ingredients in the target language.", "order": 6},
                {"question_text": "Create a prompt for a 'News Agency' game where students as journalists create reports about fictional events.", "order": 7},
                {"question_text": "Come up with a prompt to create an 'Invention Machine' game where students must invent and describe a fantastic device using technical vocabulary.", "order": 8},
                {"question_text": "Create a prompt for a 'Devil's Advocate' game where one student defends an unpopular viewpoint while others try to convince them otherwise.", "order": 9},
                {"question_text": "Come up with a prompt to create a 'Cartographers' game where students create a map of a fictional world and describe its geography, flora, and fauna.", "order": 10},
            ]
        },
        {
            "title": "Creative Assignments for Students",
            "description": "Create a prompt to generate a creative assignment.",
            "lesson_id": 5,
            "questions": [
                {"question_text": "Create a prompt that asks a student to write a diary entry from the perspective of a historical figure witnessing an important event.", "order": 1},
                {"question_text": "Come up with a prompt to create an assignment where a student needs to write a script for a short video on a social topic.", "order": 2},
                {"question_text": "Create a prompt that suggests a student interview an inanimate object (for example, an old lamp or street light).", "order": 3},
                {"question_text": "Come up with a prompt for an assignment where you need to create an advertising slogan and short text for a fantastic product.", "order": 4},
                {"question_text": "Create a prompt that asks a student to write survival instructions for a zombie apocalypse using only 10 nouns.", "order": 5},
                {"question_text": "Come up with a prompt for an assignment where a student must write a review of a non-existent movie or book based only on its title.", "order": 6},
                {"question_text": "Create a prompt that suggests a student rewrite a famous fairy tale by changing the main character's personality to the opposite.", "order": 7},
                {"question_text": "Come up with a prompt for an assignment where you need to create a playlist for a book character and explain the choice of each song.", "order": 8},
                {"question_text": "Create a prompt that asks a student to write a letter to the future, addressed to themselves in 10 years.", "order": 9},
                {"question_text": "Come up with a prompt for an assignment where a student needs to create a new superhero, describing their abilities, costume, and main enemy.", "order": 10},
            ]
        }
    ]

    for quiz_data in quizzes_data:
        quiz = await crud.get_quiz_by_title(session, quiz_data["title"])
        if not quiz:
            quiz = await crud.create_quiz(
                session,
                title=quiz_data["title"],
                description=quiz_data["description"],
                lesson_id=quiz_data["lesson_id"]
            )
            for question_data in quiz_data["questions"]:
                await crud.create_question(
                    session,
                    quiz_id=quiz.id,
                    question_text=question_data["question_text"],
                    order=question_data["order"]
                )

async def populate_text_lessons(session: AsyncSession):
    """Populates the database with lessons and steps from TEXT_LESSONS."""
    for lesson_order, lesson_data in TEXT_LESSONS.items():
        # Check if lesson already exists
        existing_lesson = await crud.get_lesson_by_title(session, title=lesson_data["title"])
        if existing_lesson:
            # Update existing lesson
            await crud.update_lesson(
                session,
                lesson_id=existing_lesson.id,
                data={'description': lesson_data['description']}
            )
            # Delete old steps
            await crud.delete_lesson_steps(session, lesson_id=existing_lesson.id)
            new_lesson = existing_lesson
        else:
            # Create the lesson
            new_lesson = await crud.create_lesson(
                session=session,
                title=lesson_data["title"],
                description=lesson_data["description"],
                lesson_type='text',
                order=lesson_order
            )



        # Create the lesson steps
        for step_number, step_content in lesson_data["steps"].items():
            await crud.create_lesson_step(
                session=session,
                lesson_id=new_lesson.id,
                step_number=step_number,
                content=step_content
            )
        print(f"Added text lesson: {new_lesson.title}")

async def populate_image_lessons(session: AsyncSession):
    """Populates the database with lessons and steps from IMAGE_LESSONS."""
    for lesson_order, lesson_data in IMAGE_LESSONS.items():
        # Check if lesson already exists
        existing_lesson = await crud.get_lesson_by_title(session, title=lesson_data["title"])
        if existing_lesson:
            # Update existing lesson
            await crud.update_lesson(
                session,
                lesson_id=existing_lesson.id,
                data={'description': lesson_data['description']}
            )
            # Delete old steps
            await crud.delete_lesson_steps(session, lesson_id=existing_lesson.id)
            new_lesson = existing_lesson
        else:
            # Create the lesson
            new_lesson = await crud.create_lesson(
                session=session,
                title=lesson_data["title"],
                description=lesson_data["description"],
                lesson_type='image',
                order=lesson_order
            )

        # Create the lesson steps
        for step_number, step_content in lesson_data["steps"].items():
            await crud.create_lesson_step(
                session=session,
                lesson_id=new_lesson.id,
                step_number=step_number,
                content=step_content
            )
        print(f"Added image lesson: {new_lesson.title}")
