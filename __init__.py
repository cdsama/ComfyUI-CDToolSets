from .qwen_image_prompt_enhancer import QwenImage21PromptEnhancerAPI
from .prompt_generator import PromptGeneratorAPI
from . import task_mode_routes

NODE_CLASS_MAPPINGS = {
    "CD_QwenImage21PromptEnhancerAPI": QwenImage21PromptEnhancerAPI,
    "CD_PromptGeneratorAPI": PromptGeneratorAPI,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CD_QwenImage21PromptEnhancerAPI": "QwenImage2.1提示词增强(API)",
    "CD_PromptGeneratorAPI": "通用提示词生成器(API)",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
