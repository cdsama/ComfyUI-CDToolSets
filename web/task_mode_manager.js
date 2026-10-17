import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_ID = "CD_PromptGeneratorAPI";
const ENDPOINT = "/cdtoolsets/task-modes";
const COMMAND = "CDToolSets.TaskModes.Manage";
let modes = [];
let builtinModes = [];
let loading;
let editor;

async function request(path, options) {
    const response = await api.fetchApi(path, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `请求失败：HTTP ${response.status}`);
    return data;
}

function updateNode(node, change = {}) {
    if (node.comfyClass !== NODE_ID) return;
    const widget = node.widgets?.find(widget => widget.name === "任务模式");
    if (!widget) return;
    if (change.previous_name && widget.value === change.previous_name) widget.value = change.name;
    const names = modes.map(mode => mode.name);
    if (!names.includes(widget.value)) {
        widget.value = names.length ? "（请选择任务模式）" : "（请先创建任务模式）";
        names.unshift(widget.value);
    }
    widget.options.values = names;
    node.setDirtyCanvas(true, true);
}

async function refreshModes(change = {}) {
    if (!loading) {
        loading = request(ENDPOINT).then(data => {
            modes = data.modes;
            builtinModes = data.builtin_modes;
        }).finally(() => { loading = null; });
    }
    await loading;
    const graphs = new Set([app.graph, app.canvas?.graph]);
    for (const graph of graphs) {
        for (const node of graph?._nodes ?? []) updateNode(node, change);
    }
}

function reportError(error) {
    app.extensionManager?.toast?.add({ severity: "error", summary: "任务模式管理", detail: error.message, life: 6000 });
}

class TaskModeEditor {
    source = "user";
    id = null;
    dirty = false;
    busy = false;

    constructor() {
        const stylesheet = document.createElement("link");
        stylesheet.rel = "stylesheet";
        stylesheet.href = new URL("./task_mode_manager.css", import.meta.url).href;
        document.head.append(stylesheet);
        this.dialog = document.createElement("dialog");
        this.dialog.className = "cd-task-dialog";
        this.dialog.setAttribute("aria-labelledby", "cd-task-title");
        const title = document.createElement("h2");
        title.id = "cd-task-title";
        title.textContent = "任务模式与系统提示词";
        const description = document.createElement("p");
        description.textContent = "用户配置用于实际运行，可自由修改。内置参考库只读，可复制到用户配置中使用或恢复。";
        const header = document.createElement("header");
        header.className = "cd-task-header";
        header.append(title, description);
        const tabs = document.createElement("div");
        tabs.className = "cd-task-tabs";
        tabs.setAttribute("role", "tablist");
        tabs.setAttribute("aria-label", "模板来源");
        this.tabs = new Map();
        for (const [source, label] of [["user", "用户配置"], ["builtin", "内置参考库"]]) {
            const tab = document.createElement("button");
            tab.type = "button";
            tab.id = `cd-task-tab-${source}`;
            tab.textContent = label;
            tab.setAttribute("role", "tab");
            tab.setAttribute("aria-controls", "cd-task-panel");
            tab.addEventListener("click", () => {
                if (this.source === source || !this.discardDraft()) return;
                this.source = source;
                this.search.value = "";
                this.select(this.currentModes[0]);
            });
            tab.addEventListener("keydown", event => {
                if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
                event.preventDefault();
                const target = event.key === "Home" ? "user" : event.key === "End" ? "builtin" : source === "user" ? "builtin" : "user";
                this.tabs.get(target).click();
                this.tabs.get(this.source).focus();
            });
            this.tabs.set(source, tab);
            tabs.append(tab);
        }
        this.search = document.createElement("input");
        this.search.type = "search";
        this.search.placeholder = "搜索任务模式…";
        this.search.setAttribute("aria-label", "搜索任务模式");
        this.search.addEventListener("input", () => this.renderList());
        this.list = document.createElement("nav");
        this.list.className = "cd-task-list";
        this.list.setAttribute("aria-label", "任务模式列表");
        this.listCount = document.createElement("span");
        this.listCount.className = "cd-task-list-count";
        const sidebar = document.createElement("aside");
        sidebar.className = "cd-task-sidebar";
        sidebar.append(this.search, this.listCount, this.list);
        this.name = document.createElement("input");
        this.name.type = "text";
        this.name.placeholder = "例如：Wan · 文生视频";
        this.prompt = document.createElement("textarea");
        this.prompt.spellcheck = false;
        this.prompt.placeholder = "填写此任务的系统提示词，可规定内容、风格和输出格式。内容会原样保存，不需要使用占位符。";
        this.requiresImages = document.createElement("input");
        this.requiresImages.type = "checkbox";
        const fields = document.createElement("div");
        fields.className = "cd-task-fields";
        for (const [text, input] of [["任务模式名称", this.name], ["系统提示词", this.prompt], ["必须提供参考图片", this.requiresImages]]) {
            const label = document.createElement("label");
            const caption = document.createElement("span");
            caption.textContent = text;
            label.append(caption, input);
            if (input === this.prompt) label.className = "cd-task-prompt-field";
            fields.append(label);
            input.addEventListener("input", () => { this.dirty = true; this.status.textContent = "有未保存的修改。"; });
        }
        this.status = document.createElement("p");
        this.status.className = "cd-task-status";
        this.status.setAttribute("role", "status");
        const actions = document.createElement("div");
        actions.className = "cd-task-actions";
        this.buttons = [];
        for (const [name, action] of [
            ["新建", () => {
                if (this.discardDraft()) {
                    this.source = "user";
                    this.search.value = "";
                    this.select();
                }
            }],
            ["复制为新模式", () => {
                const originalName = this.name.value;
                let name = originalName;
                for (let i = 1; modes.some(mode => mode.name.toLowerCase() === name.toLowerCase()); i++) {
                    name = `${originalName} 副本${i === 1 ? "" : i}`;
                }
                this.source = "user";
                this.search.value = "";
                this.id = null;
                this.name.value = name;
                this.renderList();
                this.setBusy(false);
                this.dirty = true;
                this.status.textContent = "修改名称和系统提示词后保存为新模式。";
                this.name.focus();
            }],
            ["添加缺少的内置模式", () => this.importBuiltins()],
            ["删除", () => this.remove()],
            ["保存", () => this.save()],
            ["关闭", () => { if (!this.busy && this.discardDraft()) this.dialog.close(); }],
        ]) {
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = name;
            button.addEventListener("click", action);
            if (name === "保存") this.saveButton = button;
            if (name === "删除") this.deleteButton = button;
            if (name === "复制为新模式") this.copyButton = button;
            if (name === "添加缺少的内置模式") this.importButton = button;
            actions.append(button);
            this.buttons.push(button);
        }
        this.dialog.addEventListener("cancel", event => {
            event.preventDefault();
            if (!this.busy && this.discardDraft()) this.dialog.close();
        });
        this.panel = document.createElement("div");
        this.panel.id = "cd-task-panel";
        this.panel.className = "cd-task-layout";
        this.panel.setAttribute("role", "tabpanel");
        this.panel.append(sidebar, fields);
        const footer = document.createElement("footer");
        footer.className = "cd-task-footer";
        footer.append(this.status, actions);
        this.dialog.append(header, tabs, this.panel, footer);
        document.body.append(this.dialog);
    }

    discardDraft() {
        return !this.dirty || window.confirm("当前修改尚未保存，是否放弃这些修改？");
    }

    get currentModes() {
        return this.source === "builtin" ? builtinModes : modes;
    }

    renderList() {
        const query = this.search.value.trim().toLowerCase();
        const items = this.currentModes.filter(mode => mode.name.toLowerCase().includes(query));
        const rows = [];
        if (this.source === "user" && !this.id) items.unshift({ id: null, name: "未保存的新模式" });
        for (const mode of items) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "cd-task-list-item";
            button.dataset.modeId = mode.id ?? "";
            button.disabled = this.busy;
            const active = this.id === mode.id;
            button.classList.toggle("is-active", active);
            if (active) button.setAttribute("aria-current", "true");
            const name = document.createElement("span");
            name.textContent = mode.name;
            const detail = document.createElement("small");
            detail.textContent = !mode.id ? "填写右侧内容后保存" : mode.requires_images ? "需要参考图片" : "参考图片可选";
            button.append(name, detail);
            button.addEventListener("click", () => {
                if (this.id === mode.id || !this.discardDraft()) return;
                this.select(mode.id ? mode : undefined);
            });
            rows.push(button);
        }
        if (!rows.length) {
            const empty = document.createElement("p");
            empty.className = "cd-task-empty";
            empty.textContent = query ? "没有匹配的任务模式" : "暂无任务模式，可新建或从内置库复制。";
            rows.push(empty);
        }
        this.list.replaceChildren(...rows);
        this.listCount.textContent = `${this.source === "builtin" ? "只读参考库" : "运行时配置"} · ${this.currentModes.length} 个模式`;
        for (const [source, tab] of this.tabs) {
            tab.setAttribute("aria-selected", String(source === this.source));
            tab.tabIndex = source === this.source ? 0 : -1;
        }
        this.panel.setAttribute("aria-labelledby", `cd-task-tab-${this.source}`);
    }

    select(mode) {
        this.id = mode?.id ?? null;
        this.name.value = mode?.name ?? "";
        this.prompt.value = mode?.system_prompt ?? "";
        this.requiresImages.checked = mode?.requires_images ?? false;
        this.dirty = false;
        this.renderList();
        this.setBusy(this.busy);
        this.list.querySelector(".is-active")?.scrollIntoView({ block: "nearest", inline: "nearest" });
        this.status.textContent = this.source === "builtin" ? "内置模板只读，复制到用户配置后即可编辑和保存。"
            : mode ? "修改后点击保存。" : "填写名称和系统提示词，创建自己的任务模式。";
    }

    setBusy(busy) {
        this.busy = busy;
        const readonly = this.source === "builtin";
        for (const input of [this.search, this.name, this.prompt, ...this.tabs.values(), ...this.list.querySelectorAll("button"), ...this.buttons]) input.disabled = busy;
        this.name.readOnly = readonly;
        this.prompt.readOnly = readonly;
        this.requiresImages.disabled = busy || readonly;
        this.saveButton.disabled = busy || readonly;
        this.saveButton.classList.toggle("is-primary", !readonly);
        this.deleteButton.disabled = busy || readonly;
        this.copyButton.textContent = readonly ? "复制到用户配置" : "复制为新模式";
        this.copyButton.classList.toggle("is-primary", readonly);
        this.copyButton.disabled = busy || (readonly && !this.id);
        this.importButton.hidden = !readonly;
    }

    async show(name) {
        if (this.dialog.open) { this.dialog.focus(); return; }
        this.dialog.showModal();
        this.setBusy(true);
        this.status.textContent = "正在读取任务模式…";
        try {
            await refreshModes();
            this.source = "user";
            this.search.value = "";
            this.select(modes.find(mode => mode.name === name) ?? modes[0]);
        } catch (error) {
            this.status.textContent = error.message;
        } finally {
            this.setBusy(false);
        }
    }

    async save() {
        if (this.source !== "user") return;
        const data = { name: this.name.value, system_prompt: this.prompt.value, requires_images: this.requiresImages.checked };
        if (this.id) data.id = this.id;
        const previous = modes.find(mode => mode.id === this.id);
        this.setBusy(true);
        try {
            const result = await request(ENDPOINT, {
                method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
            });
            this.dirty = false;
            await refreshModes({ previous_name: previous?.name, name: result.mode.name });
            this.select(result.mode);
            this.status.textContent = "已保存，节点任务模式列表已更新。";
        } catch (error) {
            this.status.textContent = error.message;
        } finally {
            this.setBusy(false);
        }
    }

    async remove() {
        if (this.source !== "user") return;
        if (!this.id) { this.status.textContent = "请先选择已保存的任务模式。"; return; }
        if (!window.confirm(`删除任务模式“${this.name.value}”？已有工作流中的该模式需要重新选择。`)) return;
        this.setBusy(true);
        try {
            await request(`${ENDPOINT}/${encodeURIComponent(this.id)}`, { method: "DELETE" });
            await refreshModes();
            this.select(modes[0]);
            this.status.textContent = "已删除。";
        } catch (error) {
            this.status.textContent = error.message;
        } finally {
            this.setBusy(false);
        }
    }

    async importBuiltins() {
        this.setBusy(true);
        try {
            const result = await request(`${ENDPOINT}/import-builtin`, { method: "POST" });
            await refreshModes();
            this.source = "user";
            this.search.value = "";
            this.select(modes[0]);
            this.status.textContent = `已添加 ${result.added} 个内置模式，已有同名模式保持不变。`;
        } catch (error) {
            this.status.textContent = error.message;
        } finally {
            this.setBusy(false);
        }
    }
}

function showEditor(name) {
    if (!editor) editor = new TaskModeEditor();
    return editor.show(name);
}

app.registerExtension({
    name: "CDToolSets.TaskModeManager",
    commands: [{ id: COMMAND, label: "任务模式与系统提示词", menubarLabel: "任务模式与系统提示词", function: () => showEditor() }],
    menuCommands: [{ path: ["CDToolSets"], commands: [COMMAND] }],
    setup() {
        api.addEventListener("cdtoolsets.task_modes_changed", event => refreshModes(event.detail).catch(reportError));
        return refreshModes().catch(reportError);
    },
    nodeCreated(node) {
        if (node.comfyClass !== NODE_ID) return;
        node.addWidget("button", "管理任务模式", null, () => showEditor(node.widgets.find(widget => widget.name === "任务模式")?.value), { serialize: false });
        if (modes.length) updateNode(node);
    },
});
