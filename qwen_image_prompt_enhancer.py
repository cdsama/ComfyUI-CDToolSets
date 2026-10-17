from .prompt_api import image_to_jpeg_base64, parse_result, request_prompt
from .qwen_image_prompts import LANGUAGE_RULE, SYSTEM_PROMPTS


class QwenImage21PromptEnhancerAPI:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "输入提示词": ("STRING", {"default": "", "multiline": True}),
                "任务模式": (["文生图", "图生图"], {"default": "文生图"}),
                "输出语言": (["中文", "英文"], {"default": "中文"}),
                "api_key": ("STRING", {"default": "local", "multiline": False}),
                "api_base_url": ("STRING", {"default": "http://127.0.0.1:11434/v1", "multiline": False}),
                "API接口": (["/chat/completions", "/responses"], {"default": "/chat/completions"}),
                "model": ("STRING", {"default": "qwen3.8-27b", "multiline": False}),
                "思考强度": (["none", "low", "medium", "high", "xhigh", "max"], {"default": "none"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1, "control_after_generate": True}),
            },
            "optional": {name: ("IMAGE",) for name in ("图片", "图片2", "图片3", "图片4", "图片5", "图片6", "图片7", "图片8")},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("增强提示词",)
    FUNCTION = "enhance_prompt"
    CATEGORY = "CDToolSets/提示词"

    def enhance_prompt(self, 输入提示词, 任务模式, 输出语言, api_key, api_base_url, model,
                       seed, 思考强度="none", 图片=None, 图片2=None, 图片3=None, 图片4=None,
                       图片5=None, 图片6=None, 图片7=None, 图片8=None, API接口="/chat/completions"):
        prompt = 输入提示词.strip()
        if not prompt:
            return ("",)

        images = []
        if 任务模式 == "图生图":
            images = [image_to_jpeg_base64(image) for image in (图片, 图片2, 图片3, 图片4, 图片5, 图片6, 图片7, 图片8) if image is not None]
            if not images:
                raise ValueError("图生图模式需要连接图片输入。")
        language_rule = LANGUAGE_RULE.format(language=输出语言).strip()
        system_prompt = language_rule + "\n\n" + SYSTEM_PROMPTS[任务模式] + "\n\n" + language_rule
        if 输出语言 == "中文":
            language_reminder = "输出要求：最终提示词的描述性文字必须全部使用简体中文，即使用户需求、参考图或模板示例为英文。只保留画面中明确要求的文字、专有名词和品牌名的原文；不要附带英文版本、分析或解释。"
        else:
            language_reminder = "Output requirement: Write all descriptive prose of the final prompt in English, regardless of the language of the request, reference images or template examples. Preserve the exact original wording of requested visible text, proper nouns and brand names. Return only the final prompt, without another language version, analysis or explanation."
        user_prompt = f"用户需求：\n{prompt}\n\n{language_reminder}"
        text = parse_result(request_prompt(
            system_prompt, user_prompt, images, api_key, api_base_url, model, API接口, 思考强度,
        ))
        if not text:
            raise ValueError("模型未返回最终提示词，请检查模型及思考参数。")
        return (text,)
