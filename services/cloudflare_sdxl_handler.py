import asyncio
import os
import base64
import io
from typing import Optional, Tuple
from datetime import datetime
from loguru import logger

# Try to import required packages
try:
    import aiohttp
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    aiohttp = None
    PILImage = None
    PIL_AVAILABLE = False
    logger.warning("PIL or aiohttp not found, Cloudflare SDXL functionality will be disabled.")


class CloudflareSDXLHandler:
    """Handler for AI image generation using Cloudflare Workers AI (SDXL)"""

    def __init__(self, account_id: str, api_token: str, images_dir: str = "generated_media"):
        self.account_id = account_id
        self.api_token = api_token
        self.images_dir = images_dir
        self.timeout = 120
        # API endpoint for Stable Diffusion XL
        self.api_base = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0"
        
        # Ensure images directory exists
        os.makedirs(self.images_dir, exist_ok=True)
        
        availability = self.is_available()
        logger.info(f"Cloudflare AI SDXL available: {availability}")
        logger.info(f"Account ID: {'SET' if self.account_id else 'NOT SET'}")
        logger.info(f"API Token: {'SET' if self.api_token else 'NOT SET'}")

    def is_available(self) -> bool:
        """Checks API availability"""
        if not PIL_AVAILABLE:
            return False
        available = bool(self.account_id and self.api_token)
        logger.debug(f"Cloudflare SDXL is_available: {available}")
        return available

    def _is_english(self, text: str) -> bool:
        """Simple check for English language"""
        if not text:
            return True

        # Check for Cyrillic or other non-Latin characters
        non_latin_chars = sum(1 for char in text if ord(char) > 127)
        return non_latin_chars / len(text) < 0.1  # Less than 10% non-Latin characters

    async def translate_prompt_to_english(self, prompt: str) -> str:
        """Translates prompt to English using available LLM handler
        
        Note: Translation is optional - will use original prompt if LLM unavailable
        """
        # Simple check for English language
        if self._is_english(prompt):
            return prompt

        try:
            # Import here to avoid circular imports
            from .ai_service import AIGenerationService
            service = AIGenerationService()
            
            if service.llm7_available:
                translation_prompt = f"""You are a professional translator specializing in image generation prompts.
Translate the following text to English, preserving the artistic and descriptive intent for image generation.
Keep technical terms, artistic styles, and descriptive elements intact.
Return ONLY the translated text without any additional comments or explanations.

Text to translate: {prompt}"""

                success, translated = await service.generate_text(translation_prompt)

                if success and translated and translated.strip():
                    logger.info(f"Translated prompt: {prompt[:50]}... -> {translated[:50]}...")
                    return translated

            logger.warning("LLM7 unavailable for translation, using original prompt")
            return prompt

        except Exception as e:
            logger.error(f"Error translating prompt: {e}")
            return prompt

    def enhance_prompt_for_quality(self, prompt: str) -> str:
        """
        Enhances prompt for better SDXL image quality.
        Adds quality descriptors for better results.
        """
        # Quality descriptors for SDXL
        quality_enhancers = [
            "high quality",
            "detailed",
            "sharp focus",
            "professional",
            "well composed",
            "clear",
            "realistic proportions",
            "good lighting"
        ]

        # Check if quality descriptors are already present
        prompt_lower = prompt.lower()
        has_quality_terms = any(term in prompt_lower for term in ["high quality", "detailed", "sharp", "professional", "realistic", "clear"])

        if not has_quality_terms:
            # Add quality descriptors to the end of the prompt
            enhanced_prompt = f"{prompt}, {', '.join(quality_enhancers[:4])}"
            logger.info(f"Prompt enhanced for quality: {enhanced_prompt[:100]}...")
            return enhanced_prompt

        return prompt

    async def generate_image(self, prompt: str, width: int = 1024, height: int = 1024) -> Tuple[bool, str]:
        """Generates image via Cloudflare AI SDXL
        
        Args:
            prompt: Text description of the image to generate
            width: Image width in pixels (recommended: 512-1024)
            height: Image height in pixels (recommended: 512-1024)
            
        Returns:
            Tuple of (success: bool, result: str)
            result is local file path on success, error message on failure
        """
        if not self.is_available():
            error_msg = "Cloudflare AI SDXL unavailable - missing API credentials or dependencies"
            logger.error(error_msg)
            return False, error_msg

        if not PIL_AVAILABLE:
            error_msg = "Cloudflare AI SDXL unavailable - PIL or aiohttp not installed"
            logger.error(error_msg)
            return False, error_msg

        try:
            # Translate prompt to English
            english_prompt = await self.translate_prompt_to_english(prompt)
            
            # Enhance prompt for better quality
            enhanced_prompt = self.enhance_prompt_for_quality(english_prompt)
            logger.info(f"Generating image with Cloudflare SDXL: {enhanced_prompt[:100]}...")

            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }

            # Cloudflare SDXL request format
            request_data = {
                "prompt": enhanced_prompt,
                "num_steps": 20,
                "width": width,
                "height": height,
                "guidance_scale": 7.5
            }

            result_path = None
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    self.api_base,
                    headers=headers,
                    json=request_data
                ) as response:
                    logger.info(f"Cloudflare API Response Status: {response.status}")
                    
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        
                        # Cloudflare may return either:
                        # 1. Direct binary image data (PNG)
                        # 2. JSON with base64-encoded image
                        success, result_path = await self._process_successful_response(response, content_type)
                        return success, result_path
                    else:
                        # Handle error response
                        error_text = await response.text()
                        logger.error(f"Cloudflare AI error: {response.status} {error_text}")
                        
                        # Parse error details if JSON
                        try:
                            error_json = await response.json()
                            if error_json.get("errors"):
                                error_message = error_json["errors"][0].get("message", error_text)
                            else:
                                error_message = error_text
                        except:
                            error_message = error_text
                        
                        return False, f"Cloudflare AI error: {response.status} - {error_message}"

        except asyncio.TimeoutError:
            error_msg = "Image generation timed out after 120 seconds."
            logger.warning(error_msg)
            return False, error_msg
        except aiohttp.ClientError as e:
            error_msg = f"Network error during image generation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
        except Exception as e:
            error_msg = f"An unexpected error occurred during image generation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

        # This should not be reached, but for safety
        return False, "Unexpected error in image generation"

    async def _process_successful_response(self, response: aiohttp.ClientResponse, content_type: str) -> Tuple[bool, str]:
        """Process successful response from Cloudflare AI
        
        Returns:
            Tuple of (success: bool, result: str) where result is file path or error message
        """
        try:
            # Try to parse as JSON first
            try:
                result_json = await response.json()
                if result_json.get("success") and result_json.get("result"):
                    image_data = result_json["result"]["image"]
                    image_bytes = base64.b64decode(image_data)
                else:
                    errors = result_json.get("errors", [{"message": "Unknown error"}])
                    error_msg = errors[0].get("message", "Unknown error")
                    return False, f"Cloudflare AI error: {error_msg}"
            except:
                # Not JSON, treat as binary image data
                if 'image' in content_type:
                    logger.info("Received direct binary image from Cloudflare AI")
                    image_bytes = await response.read()
                else:
                    # Check for PNG magic bytes
                    content = await response.read()
                    if content.startswith(b'\x89PNG'):
                        logger.info("Received PNG image from Cloudflare AI (detected by magic bytes)")
                        image_bytes = content
                    else:
                        return False, f"Unexpected response format. Content-Type: {content_type}"
            
            # Open and save the image
            image = PILImage.open(io.BytesIO(image_bytes))
            
            # Save to images folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"image_{timestamp}.png"
            filepath = os.path.join(self.images_dir, filename)
            image.save(filepath)
            
            logger.info(f"Successfully generated image via Cloudflare SDXL: {filepath}")
            return True, filepath
            
        except Exception as e:
            error_msg = f"Error processing image response: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg


# Singleton instance - will be initialized with config in ai_service.py
cloudflare_sdxl_handler: Optional[CloudflareSDXLHandler] = None


def initialize_cloudflare_handler(account_id: str, api_token: str, images_dir: str = "generated_media") -> CloudflareSDXLHandler:
    """Initialize or reinitialize the Cloudflare SDXL handler singleton"""
    global cloudflare_sdxl_handler
    cloudflare_sdxl_handler = CloudflareSDXLHandler(
        account_id=account_id,
        api_token=api_token,
        images_dir=images_dir
    )
    return cloudflare_sdxl_handler


def get_cloudflare_handler() -> Optional[CloudflareSDXLHandler]:
    """Get the singleton Cloudflare SDXL handler instance"""
    return cloudflare_sdxl_handler