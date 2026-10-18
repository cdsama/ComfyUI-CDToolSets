from .qwen_image_prompt_enhancer import QwenImage21PromptEnhancerAPI
from .prompt_generator import PromptGeneratorAPI
from .aspect_ratio import ClosestAspectRatio
from . import task_mode_routes

NODE_CLASS_MAPPINGS = {
    "CD_QwenImage21PromptEnhancerAPI": QwenImage21PromptEnhancerAPI,
    "CD_PromptGeneratorAPI": PromptGeneratorAPI,
    "CD_ClosestAspectRatio": ClosestAspectRatio,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CD_QwenImage21PromptEnhancerAPI": "QwenImage2.1提示词增强(API)",
    "CD_PromptGeneratorAPI": "通用提示词生成器(API)",
    "CD_ClosestAspectRatio": "获取图片比例和像素数",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
