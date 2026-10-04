import base64
import io
import json
import re

import numpy as np
import requests
from PIL import Image

from .qwen_image_prompts import LANGUAGE_RULE, SYSTEM_PROMPTS


def image_to_jpeg_base64(image):
    pixels = (image[0].detach().cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    picture = Image.fromarray(pixels).convert("RGB")
    width, height = picture.size
    if max(width, height) > 2048:
        scale = 2048 / max(width, height)
        picture = picture.resize((max(1, round(width * scale)), max(1, round(height * scale))), Image.Resampling.BICUBIC)
    buffer = io.BytesIO()
    picture.save(buffer, format="JPEG", quality=90, optimize=True, progressive=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def extract_response_text(data):
    def read_content(content):
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(part["text"] for part in content if isinstance(part, dict) and isinstance(part.get("text"), str))
        return ""

    text = read_content(data.get("output_text"))
    if text:
        return text
    text = "\n".join(read_content(item.get("content")) for item in data.get("output", []) if isinstance(item, dict))
    if text.strip():
        return text
    choices = data.get("choices", [])
    if choices:
        return read_content(choices[0].get("message", {}).get("content"))
    return ""


def parse_result(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"```thinking\b.*?```", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    text = re.sub(r"^```[^\n]*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(data, dict) and data.get("rewritten_prompt"):
                return str(data["rewritten_prompt"]).strip()
    return text


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
        url = api_base_url.strip().rstrip("/")
        if not url:
            raise ValueError("请填写 api_base_url。")
        if API接口 not in ("/chat/completions", "/responses"):
            raise ValueError("请选择 /chat/completions 或 /responses 接口。")
        for endpoint in ("/responses", "/chat/completions"):
            if url.endswith(endpoint):
                url = url[:-len(endpoint)] + API接口
                break
        else:
            url += API接口 if url.endswith("/v1") else "/v1" + API接口
        if not api_key.strip():
            raise ValueError("请填写 api_key。")
        payload = {
            "model": model.strip(),
            "temperature": 0.6,
            "enable_thinking": 思考强度 != "none",
            "reasoning_effort": 思考强度,
        }
        if API接口 == "/responses":
            content = user_prompt
            if images:
                content = [{"role": "user", "content": [
                    {"type": "input_text", "text": user_prompt},
                    *({"type": "input_image", "image_url": f"data:image/jpeg;base64,{image}"} for image in images),
                ]}]
            payload.update(instructions=system_prompt, input=content)
        else:
            content = user_prompt
            if images:
                content = [
                    {"type": "text", "text": user_prompt},
                    *({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image}"}} for image in images),
                ]
            payload["messages"] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ]
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"},
            json=payload,
            timeout=300,
        )
        if response.status_code != 200:
            raise RuntimeError(f"API 调用失败 HTTP {response.status_code}: {response.text[:1000]}")
        text = parse_result(extract_response_text(response.json()))
        if not text:
            raise ValueError("模型未返回最终提示词，请检查模型及思考参数。")
        return (text,)
