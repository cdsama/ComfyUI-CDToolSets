from .qwen_image_prompt_enhancer import QwenImage21PromptEnhancerAPI

NODE_CLASS_MAPPINGS = {
    "CD_QwenImage21PromptEnhancerAPI": QwenImage21PromptEnhancerAPI,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CD_QwenImage21PromptEnhancerAPI": "QwenImage2.1提示词增强(API)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
