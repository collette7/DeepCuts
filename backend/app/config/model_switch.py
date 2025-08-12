import os
from enum import Enum
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger('deepcuts')

class AIModel(str, Enum):
    """Available AI models"""
    CLAUDE_35_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    GEMINI_PRO = "gemini-pro"
    GEMINI_FLASH = "gemini-1.5-flash"
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_35_TURBO = "gpt-3.5-turbo"

class ModelSwitch:
    """Handles switching between different AI models"""
    
    def __init__(self):
        self.current_model = self._get_default_model()
        self.fallback_models = [
            AIModel.CLAUDE_35_SONNET,
            AIModel.GEMINI_PRO,
            AIModel.GPT_4_TURBO,
            AIModel.CLAUDE_3_HAIKU
        ]
    
    def _get_default_model(self) -> AIModel:
        """Get default model from environment or use Claude Sonnet"""
        model_name = os.getenv("DEFAULT_AI_MODEL", AIModel.CLAUDE_35_SONNET.value)
        try:
            return AIModel(model_name)
        except ValueError:
            logger.warning(f"Invalid model name: {model_name}, using default")
            return AIModel.CLAUDE_35_SONNET
    
    def switch_to(self, model: AIModel) -> bool:
        """Switch to a specific model"""
        try:
            if self._is_model_available(model):
                self.current_model = model
                logger.info(f"Switched to model: {model.value}")
                return True
            else:
                logger.warning(f"Model {model.value} is not available")
                return False
        except Exception as e:
            logger.error(f"Error switching model: {e}")
            return False
    
    def _is_model_available(self, model: AIModel) -> bool:
        """Check if model is available (has API key configured)"""
        if model in [AIModel.CLAUDE_35_SONNET, AIModel.CLAUDE_3_OPUS, AIModel.CLAUDE_3_HAIKU]:
            return bool(os.getenv("CLAUDE_API_KEY"))
        elif model in [AIModel.GEMINI_PRO, AIModel.GEMINI_FLASH]:
            return bool(os.getenv("GEMINI_API_KEY"))
        elif model in [AIModel.GPT_4_TURBO, AIModel.GPT_35_TURBO]:
            return bool(os.getenv("OPENAI_API_KEY"))
        return False
    
    def get_available_models(self) -> List[AIModel]:
        """Get list of available models based on configured API keys"""
        available = []
        for model in AIModel:
            if self._is_model_available(model):
                available.append(model)
        return available
    
    def fallback_to_next(self) -> Optional[AIModel]:
        """Fallback to next available model in the fallback chain"""
        for model in self.fallback_models:
            if model != self.current_model and self._is_model_available(model):
                self.current_model = model
                logger.info(f"Fell back to model: {model.value}")
                return model
        logger.error("No fallback models available")
        return None
    
    def get_model_client(self):
        """Get the appropriate client for the current model"""
        if self.current_model in [AIModel.CLAUDE_35_SONNET, AIModel.CLAUDE_3_OPUS, AIModel.CLAUDE_3_HAIKU]:
            import anthropic
            return anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        elif self.current_model in [AIModel.GEMINI_PRO, AIModel.GEMINI_FLASH]:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            return genai.GenerativeModel(self.current_model.value)
        elif self.current_model in [AIModel.GPT_4_TURBO, AIModel.GPT_35_TURBO]:
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            return openai
        return None
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get configuration for current model"""
        configs = {
            AIModel.CLAUDE_35_SONNET: {
                "max_tokens": 4000,
                "temperature": 0.7,
                "provider": "anthropic"
            },
            AIModel.CLAUDE_3_OPUS: {
                "max_tokens": 4000,
                "temperature": 0.7,
                "provider": "anthropic"
            },
            AIModel.CLAUDE_3_HAIKU: {
                "max_tokens": 4000,
                "temperature": 0.7,
                "provider": "anthropic"
            },
            AIModel.GEMINI_PRO: {
                "max_tokens": 4000,
                "temperature": 0.7,
                "provider": "google"
            },
            AIModel.GEMINI_FLASH: {
                "max_tokens": 8192,
                "temperature": 0.7,
                "provider": "google"
            },
            AIModel.GPT_4_TURBO: {
                "max_tokens": 4000,
                "temperature": 0.7,
                "provider": "openai"
            },
            AIModel.GPT_35_TURBO: {
                "max_tokens": 4000,
                "temperature": 0.7,
                "provider": "openai"
            }
        }
        return configs.get(self.current_model, configs[AIModel.CLAUDE_35_SONNET])

# Global instance
model_switch = ModelSwitch()