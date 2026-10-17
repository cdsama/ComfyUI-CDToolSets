import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import uuid

BUILTIN_FILE = Path(__file__).parent / "data" / "builtin_task_modes.json"
TASK_FILE = Path(__file__).parent / "data" / "task_modes.json"
LOCK = threading.RLock()


def read_modes(path):
    modes = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(modes, list):
        raise ValueError("任务模式文件必须是 JSON 数组。")
    names, ids = set(), set()
    for mode in modes:
        validate_mode(mode)
        if not isinstance(mode.get("id"), str) or not mode["id"]:
            raise ValueError("任务模式缺少有效 id。")
        if mode["id"] in ids or mode["name"].casefold() in names:
            raise ValueError("任务模式文件包含重复名称或 id。")
        ids.add(mode["id"])
        names.add(mode["name"].casefold())
    return modes


def load_builtin_modes():
    return read_modes(BUILTIN_FILE)


def load_modes():
    with LOCK:
        if not TASK_FILE.exists():
            write_modes(load_builtin_modes())
        return read_modes(TASK_FILE)


def import_builtin_modes():
    with LOCK:
        modes = load_modes()
        names = {mode["name"].casefold() for mode in modes}
        additions = [dict(mode, id=uuid.uuid4().hex) for mode in load_builtin_modes() if mode["name"].casefold() not in names]
        if additions:
            write_modes(modes + additions)
        return len(additions)


def validate_mode(mode):
    if not isinstance(mode, dict):
        raise ValueError("任务模式必须是对象。")
    for key, label in (("name", "名称"), ("system_prompt", "系统提示词")):
        if not isinstance(mode.get(key), str) or not mode[key].strip():
            raise ValueError(f"请填写任务模式的{label}。")
    if not isinstance(mode.get("requires_images", False), bool):
        raise ValueError("参考图片要求必须是布尔值。")


def write_modes(modes):
    TASK_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=TASK_FILE.parent, suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            json.dump(modes, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary, TASK_FILE)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_mode(data):
    validate_mode(data)
    with LOCK:
        modes = load_modes()
        mode_id = data.get("id")
        previous = next((mode for mode in modes if mode["id"] == mode_id), None)
        if mode_id and previous is None:
            raise KeyError("任务模式已被删除，请刷新列表。")
        name = data["name"].strip()
        if any(mode["name"].casefold() == name.casefold() and mode["id"] != mode_id for mode in modes):
            raise ValueError("已有同名任务模式，请更换名称。")
        saved = {"id": previous["id"] if previous else uuid.uuid4().hex, "name": name,
                 "system_prompt": data["system_prompt"], "requires_images": data.get("requires_images", False)}
        modes = [saved if mode["id"] == mode_id else mode for mode in modes]
        if previous is None:
            modes.append(saved)
        write_modes(modes)
        return saved, previous["name"] if previous else None


def delete_mode(mode_id):
    with LOCK:
        modes = load_modes()
        if not any(mode["id"] == mode_id for mode in modes):
            raise KeyError("任务模式不存在。")
        write_modes([mode for mode in modes if mode["id"] != mode_id])


def get_mode(name):
    for mode in load_modes():
        if mode["name"] == name:
            return mode
    raise ValueError(f"任务模式“{name}”不存在，请打开任务模式管理重新选择。")


def mode_fingerprint(name):
    data = json.dumps(get_mode(name), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
