from aiohttp import web
from server import PromptServer

from .task_modes import delete_mode, import_builtin_modes, load_builtin_modes, load_modes, save_mode


routes = PromptServer.instance.routes


@routes.get("/cdtoolsets/task-modes")
async def list_task_modes(request):
    try:
        return web.json_response({"modes": load_modes(), "builtin_modes": load_builtin_modes()})
    except (ValueError, OSError) as error:
        return web.json_response({"error": str(error)}, status=500)


@routes.post("/cdtoolsets/task-modes")
async def save_task_mode(request):
    try:
        mode, previous_name = save_mode(await request.json())
    except KeyError as error:
        return web.json_response({"error": error.args[0]}, status=404)
    except ValueError as error:
        return web.json_response({"error": str(error)}, status=400)
    except OSError as error:
        return web.json_response({"error": str(error)}, status=500)
    PromptServer.instance.send_sync("cdtoolsets.task_modes_changed", {"previous_name": previous_name, "name": mode["name"]})
    return web.json_response({"mode": mode})


@routes.post("/cdtoolsets/task-modes/import-builtin")
async def import_task_modes(request):
    try:
        added = import_builtin_modes()
    except (ValueError, OSError) as error:
        return web.json_response({"error": str(error)}, status=500)
    PromptServer.instance.send_sync("cdtoolsets.task_modes_changed", {})
    return web.json_response({"added": added})


@routes.delete("/cdtoolsets/task-modes/{mode_id}")
async def delete_task_mode(request):
    try:
        delete_mode(request.match_info["mode_id"])
    except KeyError as error:
        return web.json_response({"error": error.args[0]}, status=404)
    except ValueError as error:
        return web.json_response({"error": str(error)}, status=400)
    except OSError as error:
        return web.json_response({"error": str(error)}, status=500)
    PromptServer.instance.send_sync("cdtoolsets.task_modes_changed", {})
    return web.json_response({"ok": True})
