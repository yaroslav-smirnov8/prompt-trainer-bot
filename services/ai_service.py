import asyncio
import os
import uuid
import re
from typing import Optional, Tuple, Union, List
import json

import aiohttp
from aiohttp import ClientTimeout
from loguru import logger

# Try to import required packages for LLM7 and Together AI
try:
    import requests
    API_AVAILABLE = True
except ImportError:
    requests = None
    API_AVAILABLE = False
    logger.warning("requests package not found, generation features will be disabled.")

# Store API keys
LLM7_API_KEY = os.getenv("LLM7_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# Check if API keys are available
TEXT_GEN_AVAILABLE = bool(LLM7_API_KEY)
IMAGE_GEN_AVAILABLE = bool(TOGETHER_API_KEY)
API_AVAILABLE = API_AVAILABLE and (TEXT_GEN_AVAILABLE or IMAGE_GEN_AVAILABLE)


class AIGenerationService:
    """Service for generating text and images using LLM7 and Together AI"""

    def __init__(self, images_dir: str = "generated_media"):
        self.images_dir = images_dir
        os.makedirs(self.images_dir, exist_ok=True)
        self.available = API_AVAILABLE
        self.llm7_available = TEXT_GEN_AVAILABLE
        self.together_available = IMAGE_GEN_AVAILABLE

        if self.available:
            if self.llm7_available:
                logger.info("Text generation service initialized with LLM7.")
            else:
                logger.warning("LLM7 API key not provided, text generation will be disabled.")

            if self.together_available:
                logger.info("Image generation service initialized with Together AI Flux Schnell.")
            else:
                logger.warning("Together API key not provided, image generation will be disabled.")
        else:
            logger.warning("LLM7/Together AI is not available or configured, generation features will be disabled.")


    async def generate_text(self, prompt: str, provider_name: Optional[str] = None) -> Tuple[bool, str]:
        """Generate text based on prompt"""
        if not self.llm7_available:
            return False, "Text generation is not available"

        try:
            logger.info(f"Generating text with LLM7 prompt: '{prompt}'")

            # Use requests to call LLM7 API
            headers = {
                "Authorization": f"Bearer {LLM7_API_KEY}",
                "Content-Type": "application/json"
            }

            request_data = {
                "model": "gpt-4.1-2025-04-14",  # Default model
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "stream": False
            }

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    "https://api.llm7.io/v1/chat/completions",
                    headers=headers,
                    json=request_data,
                    timeout=60
                )
            )

            if response.status_code == 200:
                response_data = response.json()
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    content = response_data["choices"][0]["message"]["content"]
                    logger.info(f"Text generation successful")
                    return True, content
                else:
                    logger.error(f"Unexpected response format from LLM7: {response_data}")
                    return False, "Unexpected response format from LLM7"
            else:
                error_text = response.text
                logger.error(f"LLM7 API error: {response.status_code} - {error_text}")
                return False, f"LLM7 API error: {response.status_code}"

        except asyncio.TimeoutError:
            logger.warning("Text generation timed out after 60 seconds.")
            return False, "Text generation timed out."
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during text generation: {e}", exc_info=True)
            return False, f"Network error during generation: {str(e)}"
        except Exception as e:
            logger.error(f"Error generating text: {e}", exc_info=True)
            return False, f"Error generating text: {str(e)}"

    async def generate_image(self, prompt: str) -> Tuple[bool, Union[str, bytes]]:
        """Generate image based on prompt"""
        if not self.together_available:
            logger.error("Image generation is not available because Together AI key is not provided.")
            return False, "Image generation is not available"

        logger.info(f"Generating image with Together AI Flux Schnell prompt: '{prompt}'")

        try:
            logger.info("Attempting to generate image with Together AI...")

            headers = {
                "Authorization": f"Bearer {TOGETHER_API_KEY}",
                "Content-Type": "application/json"
            }

            request_data = {
                "model": "black-forest-labs/FLUX.1-schnell",  # Flux Schnell model
                "prompt": prompt,
                "width": 1024,
                "height": 1024,
                "steps": 4,
                "n": 1,
                "response_format": "url"
            }

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    "https://api.together.xyz/v1/images/generations",
                    headers=headers,
                    json=request_data,
                    timeout=120
                )
            )

            if response.status_code == 200:
                result = response.json()

                if result.get("data") and len(result["data"]) > 0:
                    image_url = result["data"][0]["url"]
                    logger.info(f"Successfully generated image via Together AI: {image_url[:100]}...")

                    # Return the URL directly to Telegram for immediate delivery
                    # This avoids the slow download process and lets Telegram handle the image directly
                    logger.info(f"Returning image URL directly to handler for immediate Telegram delivery: {image_url}")
                    return True, image_url
                else:
                    logger.error(f"No image data in Together AI response: {result}")
                    return False, "No image data in response from Together AI"
            else:
                error_text = response.text
                logger.error(f"Together AI API error: {response.status_code} - {error_text}")
                return False, f"Together AI API error: {response.status_code}"

        except asyncio.TimeoutError:
            logger.warning("Image generation timed out after 120 seconds.")
            return False, "Image generation timed out."
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during image generation: {e}", exc_info=True)
            return False, f"Network error during generation: {str(e)}"
        except Exception as e:
            logger.error(f"An unexpected error occurred during image generation: {e}", exc_info=True)
            return False, f"An error occurred during image generation: {e}"


async def evaluate_answer(question: str, answer: str) -> dict:
    """Evaluate user's answer to a quiz question using AI service.

    Args:
        question: The quiz question text
        answer: User's answer text

    Returns:
        dict with evaluation results containing:
        - is_correct (bool): Whether the answer is correct
        - score (float): Score from 0 to 10
        - feedback (str): Feedback explaining the evaluation
    """
    import inspect
    frame = inspect.currentframe().f_back
    caller_info = f"{frame.f_code.co_filename}:{frame.f_code.co_name}:{frame.f_lineno}"
    logger.info(f"evaluate_answer called from {caller_info}")
    logger.info(f"Evaluating answer for question: '{question[:50]}...'")
    service = AIGenerationService()
    if not service.available:
        logger.warning("AI service is not available for evaluation")
        return {
            "is_correct": False,
            "score": 0,
            "feedback": "Answer evaluation service is unavailable."
        }

    prompt = f"""Evaluate the answer to the question on a scale from 0 to 10. Response format - JSON:
    {{
        "is_correct": true/false, // Is the answer correct
        "score": 0-10, // Score from 0 to 10
        "feedback": "string" // Explanation of the score
    }}

    Question: {question}
    Answer: {answer}
    """

    logger.info("Sending evaluation prompt to AI service")
    success, response = await service.generate_text(prompt)
    if not success:
        logger.error(f"Failed to evaluate answer: {response}")
        return {
            "is_correct": False,
            "score": 0,
            "feedback": "Error evaluating answer."
        }
    
    try:
        import json
        logger.info(f"Parsing evaluation response: {response[:100]}...")
        # Clean the response to extract only the JSON part
        if isinstance(response, str):
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                logger.info(f"Parsed JSON result: {result}")
                return {
                    "is_correct": bool(result.get("is_correct", False)),
                    "score": float(result.get("score", 0)),
                    "feedback": str(result.get("feedback", "No feedback."))
                }
            else:
                raise ValueError("No JSON object found in the response")
        else:
            raise ValueError("Response is not a string, cannot parse for JSON.")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error parsing evaluation response: {e}")
        logger.error(f"Raw response: {response}")
        return {
            "is_correct": False,
            "score": 0,
            "feedback": "Error processing evaluation."
        }
    except Exception as e:
        logger.error(f"An unexpected error occurred during evaluation parsing: {e}")
        logger.error(f"Raw response: {response}")
        return {
            "is_correct": False,
            "score": 0,
            "feedback": "Unexpected error processing answer."
        }


async def generate_text(prompt: str) -> str:
    """Generate text based on prompt using AI service.

    Args:
        prompt: The input prompt text

    Returns:
        str: Generated text or error message
    """
    logger.info(f"Global generate_text called with prompt: '{prompt[:50]}...'")
    service = AIGenerationService()
    if not service.available:
        logger.warning("AI service is not available for text generation")
        return "Text generation service unavailable."

    logger.info("Calling AIGenerationService.generate_text method")
    success, response = await service.generate_text(prompt)
    if not success:
        logger.error(f"Failed to generate text: {response}")
        return "Error generating text."

    logger.info("Text generation successful")
    return response


async def evaluate_text_prompt_quality(prompt: str) -> dict:
    """Evaluate quality of text prompts using AI service.

    Args:
        prompt: The text prompt to evaluate

    Returns:
        dict with evaluation results:
        - ai_score (float): Overall AI score 0-10
        - clarity_score (float): Clarity score 0-3
        - structure_score (float): Structure score 0-2
        - creativity_score (float): Creativity score 0-1
        - feedback (str): Detailed feedback
        - improvement_suggestions (str): Suggestions for improvement
    """
    logger.info(f"Evaluating text prompt quality: '{prompt[:50]}...'")
    service = AIGenerationService()
    if not service.available:
        logger.warning("AI service is not available for prompt evaluation")
        return {
            "ai_score": 0,
            "clarity_score": 0,
            "structure_score": 0,
            "creativity_score": 0,
            "feedback": "Prompt evaluation service is unavailable.",
            "improvement_suggestions": ""
        }

    evaluation_prompt = f"""Evaluate the quality of this text prompt for AI on the following criteria:

1. Clarity and specificity (0-3): clear formulation, no ambiguity
2. Structure (0-2): logical sequence, use of context
3. Creative approach (0-1): non-standard but effective formulations

Return response in JSON format:
{{
    "clarity_score": 0-3,
    "structure_score": 0-2,
    "creativity_score": 0-1,
    "ai_score": 0-10,
    "feedback": "detailed feedback in English",
    "improvement_suggestions": "specific suggestions for improvement"
}}

Prompt to evaluate: "{prompt}"
"""

    logger.info("Sending text prompt evaluation to AI service")
    success, response = await service.generate_text(evaluation_prompt)
    if not success:
        logger.error(f"Failed to evaluate text prompt: {response}")
        return {
            "ai_score": 0,
            "clarity_score": 0,
            "structure_score": 0,
            "creativity_score": 0,
            "feedback": "Error evaluating prompt.",
            "improvement_suggestions": ""
        }
    
    try:
        import json
        logger.info(f"Parsing text prompt evaluation response: {response[:100]}...")
        
        if isinstance(response, str) and ("<!DOCTYPE html>" in response or "<html>" in response):
            logger.error("Evaluation response is HTML page instead of JSON")
            return {
                "ai_score": 0,
                "clarity_score": 0,
                "structure_score": 0,
                "creativity_score": 0,
                "feedback": "Evaluation service returned web page instead of result.",
                "improvement_suggestions": "Please try again later."
            }
        
        if isinstance(response, str):
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                logger.info(f"Parsed text prompt evaluation: {result}")
                return {
                    "ai_score": float(result.get("ai_score", 0)),
                    "clarity_score": float(result.get("clarity_score", 0)),
                    "structure_score": float(result.get("structure_score", 0)),
                    "creativity_score": float(result.get("creativity_score", 0)),
                    "feedback": str(result.get("feedback", "No feedback.")),
                    "improvement_suggestions": str(result.get("improvement_suggestions", ""))
                }
            else:
                raise ValueError("No JSON object found in the response")
        else:
            raise ValueError("Response is not a string, cannot parse for JSON.")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error parsing text prompt evaluation: {e}")
        logger.error(f"Raw response: {response}")
        return {
            "ai_score": 0,
            "clarity_score": 0,
            "structure_score": 0,
            "creativity_score": 0,
            "feedback": "Error processing prompt evaluation.",
            "improvement_suggestions": ""
        }


async def evaluate_image_prompt_quality(prompt: str) -> dict:
    """Evaluate quality of image prompts using AI service.

    Args:
        prompt: The image prompt to evaluate

    Returns:
        dict with evaluation results:
        - ai_score (float): Overall AI score 0-10
        - technical_score (float): Technical accuracy 0-3
        - structure_score (float): Structure score 0-2
        - creativity_score (float): Creativity score 0-1
        - feedback (str): Detailed feedback
        - improvement_suggestions (str): Suggestions for improvement
    """
    logger.info(f"Evaluating image prompt quality: '{prompt[:50]}...'")
    service = AIGenerationService()
    if not service.available:
        logger.warning("AI service is not available for image prompt evaluation")
        return {
            "ai_score": 0,
            "technical_score": 0,
            "structure_score": 0,
            "creativity_score": 0,
            "feedback": "Prompt evaluation service is unavailable.",
            "improvement_suggestions": ""
        }

    evaluation_prompt = f"""Evaluate the quality of this prompt for image generation in Stable Diffusion XL by criteria:

1. Technical accuracy (0-3): correct use of tags, modifiers, terms
2. Structure (0-2): logical sequence of description elements
3. Creativity (0-1): originality of approach, interesting details

Good SDXL prompt contains: main subject, style, details, quality (masterpiece, best quality), resolution, lighting, composition.

IMPORTANT: All improvement suggestions must be in ENGLISH, as image generation only works with English prompts.

Return response in JSON format:
{{
    "technical_score": 0-3,
    "structure_score": 0-2,
    "creativity_score": 0-1,
    "ai_score": 0-10,
    "feedback": "detailed feedback in English",
    "improvement_suggestions": "specific suggestions for SDXL improvement IN ENGLISH"
}}

Prompt to evaluate: "{prompt}"
"""

    logger.info("Sending image prompt evaluation to AI service")
    success, response = await service.generate_text(evaluation_prompt)
    if not success:
        logger.error(f"Failed to evaluate image prompt: {response}")
        return {
            "ai_score": 0,
            "technical_score": 0,
            "structure_score": 0,
            "creativity_score": 0,
            "feedback": "Error evaluating prompt.",
            "improvement_suggestions": ""
        }
    
    try:
        import json
        logger.info(f"Parsing image prompt evaluation response: {response[:100]}...")
        
        if isinstance(response, str) and ("<!DOCTYPE html>" in response or "<html>" in response):
            logger.error("Image evaluation response is HTML page instead of JSON")
            return {
                "ai_score": 0,
                "technical_score": 0,
                "structure_score": 0,
                "creativity_score": 0,
                "feedback": "Evaluation service returned web page instead of result.",
                "improvement_suggestions": "Please try again later."
            }
        
        if isinstance(response, str):
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                logger.info(f"Parsed image prompt evaluation: {result}")
                return {
                    "ai_score": float(result.get("ai_score", 0)),
                    "technical_score": float(result.get("technical_score", 0)),
                    "structure_score": float(result.get("structure_score", 0)),
                    "creativity_score": float(result.get("creativity_score", 0)),
                    "feedback": str(result.get("feedback", "No feedback.")),
                    "improvement_suggestions": str(result.get("improvement_suggestions", ""))
                }
            else:
                raise ValueError("No JSON object found in the response")
        else:
            raise ValueError("Response is not a string, cannot parse for JSON.")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error parsing image prompt evaluation: {e}")
        logger.error(f"Raw response: {response}")
        return {
            "ai_score": 0,
            "technical_score": 0,
            "structure_score": 0,
            "creativity_score": 0,
            "feedback": "Error processing prompt evaluation.",
            "improvement_suggestions": ""
        }


async def evaluate_prompt_quality(prompt: str, prompt_type: str) -> dict:
    """Universal prompt quality evaluator that routes to specific evaluators.

    Args:
        prompt: The prompt to evaluate
        prompt_type: 'text' or 'image'

    Returns:
        dict with evaluation results
    """
    logger.info(f"Evaluating {prompt_type} prompt quality")

    if prompt_type == "text":
        return await evaluate_text_prompt_quality(prompt)
    elif prompt_type == "image":
        return await evaluate_image_prompt_quality(prompt)
    else:
        logger.error(f"Unknown prompt type: {prompt_type}")
        return {
            "ai_score": 0,
            "technical_score": 0,
            "clarity_score": 0,
            "structure_score": 0,
            "creativity_score": 0,
            "feedback": "Unknown prompt type.",
            "improvement_suggestions": ""
        }


def calculate_rating_bonus(ai_score: float) -> float:
    """Calculate rating bonus points based on prompt quality score.
    
    Args:
        ai_score: AI evaluation score (0-10)
        
    Returns:
        float: Bonus points to add to user's rating
    """
    if ai_score >= 8.0:
        return 3.0
    elif ai_score >= 6.0:
        return 2.0
    elif ai_score >= 4.0:
        return 1.0
    else:
        return 0.5  # Encouragement bonus for participation


# Create a singleton for the service
ai_service = AIGenerationService()

# For backward compatibility
G4FService = AIGenerationService
g4f_service = G4FService()
