import base64
import io
import json
import re

import numpy as np
import requests
from PIL import Image

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


def strip_thinking(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r"```thinking\b.*?```", "", text, flags=re.DOTALL | re.IGNORECASE).strip()


def parse_result(text):
    text = strip_thinking(text)
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


def request_prompt(system_prompt, user_prompt, images, api_key, api_base_url, model, api_interface, reasoning_effort):
    url = api_base_url.strip().rstrip("/")
    if not url:
        raise ValueError("请填写 api_base_url。")
    if api_interface not in ("/chat/completions", "/responses"):
        raise ValueError("请选择 /chat/completions 或 /responses 接口。")
    for endpoint in ("/responses", "/chat/completions"):
        if url.endswith(endpoint):
            url = url[:-len(endpoint)] + api_interface
            break
    else:
        url += api_interface if url.endswith("/v1") else "/v1" + api_interface
    if not api_key.strip():
        raise ValueError("请填写 api_key。")
    payload = {
        "model": model.strip(),
        "temperature": 0.6,
        "enable_thinking": reasoning_effort != "none",
        "reasoning_effort": reasoning_effort,
    }
    if api_interface == "/responses":
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
    return extract_response_text(response.json())
