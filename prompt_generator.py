from comfy_api.latest import io

from .prompt_api import image_to_jpeg_base64, request_prompt, strip_thinking
from .task_modes import get_mode, load_modes, mode_fingerprint


class PromptGeneratorAPI(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        modes = [mode["name"] for mode in load_modes()]
        return io.Schema(
            node_id="CD_PromptGeneratorAPI",
            display_name="通用提示词生成器(API)",
            category="CDToolSets/提示词",
            inputs=[
                io.String.Input("输入提示词", multiline=True, default=""),
                io.Combo.Input("任务模式", options=modes or ["（请先创建任务模式）"]),
                io.Combo.Input("输出语言", options=["中文", "英文", "跟随模板"], default="中文"),
                io.String.Input("api_key", default="local"),
                io.String.Input("api_base_url", default="http://127.0.0.1:11434/v1"),
                io.Combo.Input("API接口", options=["/chat/completions", "/responses"], default="/chat/completions"),
                io.String.Input("model", default="qwen3.8-27b"),
                io.Combo.Input("思考强度", options=["none", "low", "medium", "high", "xhigh", "max"], default="none"),
                io.Int.Input("seed", default=0, min=0, max=0xffffffffffffffff, control_after_generate=True),
                io.Autogrow.Input("图片", optional=True, template=io.Autogrow.TemplatePrefix(
                    io.Image.Input("image"), prefix="image_", min=0, max=100,
                )),
            ],
            outputs=[io.String.Output(display_name="提示词")],
        )

    @classmethod
    def fingerprint_inputs(cls, 任务模式, **kwargs):
        return mode_fingerprint(任务模式)

    @classmethod
    def execute(cls, 输入提示词, 任务模式, 输出语言, api_key, api_base_url, API接口, model,
                思考强度, seed, 图片=None):
        mode = get_mode(任务模式)
        images = [image_to_jpeg_base64(image) for name, image in sorted(
            (图片 or {}).items(), key=lambda item: int(item[0].rsplit("_", 1)[-1]),
        ) if image is not None]
        if mode.get("requires_images") and not images:
            raise ValueError(f"任务模式“{任务模式}”需要连接参考图片。")
        system_prompt = mode["system_prompt"]
        user_prompt = 输入提示词.strip()
        if 输出语言 != "跟随模板":
            language = "简体中文" if 输出语言 == "中文" else "English"
            rule = (f"输出语言要求（优先于模板示例的语言）：描述性文字必须使用 {language}。"
                    "保持模板指定的输出结构、JSON键名、标签和代码不变；保留用户要求的画面文字、歌词、对白、品牌名及专有名词的原文。"
                    "只输出模板要求的最终结果，不附加分析或另一语言版本。")
            system_prompt = f"{rule}\n\n{system_prompt}\n\n{rule}"
            user_prompt = f"{user_prompt}\n\n{rule}"
        result = strip_thinking(request_prompt(
            system_prompt, user_prompt, images, api_key, api_base_url, model, API接口, 思考强度,
        ))
        if not result:
            raise ValueError("模型未返回最终提示词，请检查模型及思考参数。")
        return io.NodeOutput(result)
