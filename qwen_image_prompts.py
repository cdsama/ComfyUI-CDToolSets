from .task_modes import load_builtin_modes


_modes = {mode["id"]: mode["system_prompt"] for mode in load_builtin_modes()}
SYSTEM_PROMPTS = {
    "文生图": _modes["qwen-image-21-text"],
    "图生图": _modes["qwen-image-21-edit"],
}
del _modes

LANGUAGE_RULE = '\n最终语言规则（优先级最高）：节点选择的输出语言是“{language}”。除用户明确要求显示在图片中的文字、专有名词和品牌名外，最终提示词的全部描述性文字必须使用{language}。不要根据用户输入语言、模板示例语言或图片中的文字语言改变这个选择。只输出最终提示词纯文本，不输出 JSON、字段名、Markdown、分析过程、思考内容或解释。\n当前为 API 模式：只输出最终增强后的提示词纯文本，不要输出 JSON、字段名、代码块、分析或解释。'
