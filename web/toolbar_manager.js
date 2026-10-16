import { app } from "../../scripts/app.js";
import { ComfyButton } from "../../scripts/ui/components/button.js";

const STORAGE_KEY = "CDToolSets.Toolbar.Hidden";
const HIDDEN_ATTRIBUTE = "data-cd-toolbar-hidden";
const COMMAND = "CDToolSets.Toolbar.Manage";
const INTERACTIVE = "button, a, input, select, [role='button']";

function readHidden() {
    try {
        const value = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
        return new Set(Array.isArray(value) ? value.filter(key => typeof key === "string") : []);
    } catch {
        return new Set();
    }
}

function textOf(element) {
    return (element.getAttribute("title") || element.getAttribute("aria-label") || element.textContent || "")
        .replace(/\d+(?:[.,]\d+)?\s*(?:%|°[CF]?|℃)/g, "")
        .replace(/\s+/g, " ").trim().slice(0, 120);
}

function identityOf(element) {
    if (element.id) return `id:${element.id}`;
    if (element.dataset.testid) return `testid:${element.dataset.testid}`;
    const icon = element.querySelector("i, svg");
    const iconClass = [...(icon?.classList ?? [])].filter(name => name.startsWith("mdi-") || name.startsWith("icon-["));
    if (iconClass.length) return `icon:${iconClass.sort().join(" ")}`;
    if (element.title) return `title:${element.title}`;
    if (element.getAttribute("aria-label")) return `label:${element.getAttribute("aria-label")}`;
    if (element.classList.length) return `class:${[...element.classList].sort().join(" ")}`;
    return `text:${textOf(element) || element.tagName.toLowerCase()}`;
}

class ToolbarManager {
    hidden = readHidden();
    entries = [];
    identities = new WeakMap();
    roots = new Map();
    scheduled = false;
    dialog = null;
    rows = null;
    search = "";
    saveError = false;

    constructor() {
        this.button = new ComfyButton({
            icon: "tune",
            tooltip: "CDToolSets 顶部工具栏管理",
            action: () => this.show(),
        });
        this.button.element.dataset.cdToolbarManager = "true";
    }

    start() {
        const stylesheet = document.createElement("link");
        stylesheet.rel = "stylesheet";
        stylesheet.href = new URL("./toolbar_manager.css", import.meta.url).href;
        document.head.append(stylesheet);

        // Watch structure only: resource monitors update text and styles frequently.
        this.documentObserver = new MutationObserver(records => {
            const roots = [...this.roots.keys()];
            if (app.menu?.element) roots.push(app.menu.element);
            if (records.some(record => {
                if (record.target.closest?.(".cd-toolbar-dialog")) return false;
                const nodes = [...record.addedNodes, ...record.removedNodes].filter(node => node instanceof HTMLElement);
                if (!nodes.length) return false;
                if (roots.some(root => root.contains(record.target))) return true;
                return nodes.some(node => roots.some(root => node.contains(root)) ||
                    node.matches('[data-testid="action-bar-buttons"]') || node.querySelector('[data-testid="action-bar-buttons"]'));
            })) this.schedule();
        });
        this.documentObserver.observe(document.body, { childList: true, subtree: true });
        window.addEventListener("storage", event => {
            if (event.key === STORAGE_KEY || event.key === null) {
                this.hidden = readHidden();
                this.scan();
            }
        });
        this.scan();
    }

    schedule() {
        if (this.scheduled) return;
        this.scheduled = true;
        requestAnimationFrame(() => {
            this.scheduled = false;
            this.scan();
        });
    }

    scan() {
        const settingsGroup = app.menu?.settingsGroup;
        if (settingsGroup && !settingsGroup.element.contains(this.button.element)) {
            settingsGroup.append(this.button);
        }
        const currentRoots = new Map();
        if (app.menu?.element) currentRoots.set(app.menu.element, "legacy");
        for (const root of document.querySelectorAll('[data-testid="action-bar-buttons"]')) {
            currentRoots.set(root, "actionbar");
        }
        for (const [root, observer] of this.roots) {
            if (!currentRoots.has(root)) {
                observer.disconnect();
                this.roots.delete(root);
                for (const element of root.querySelectorAll(`[${HIDDEN_ATTRIBUTE}], [data-cd-toolbar-empty]`)) {
                    element.removeAttribute(HIDDEN_ATTRIBUTE);
                    element.removeAttribute("data-cd-toolbar-empty");
                }
            }
        }
        for (const root of currentRoots.keys()) {
            if (this.roots.has(root)) continue;
            const observer = new MutationObserver(() => this.schedule());
            observer.observe(root, { attributes: true, subtree: true, attributeFilter: ["title", "aria-label"] });
            this.roots.set(root, observer);
        }

        const entries = [];
        const counts = new Map();
        const seen = new Set();
        const collect = (element, scope) => {
            if (element.dataset.cdToolbarManager) return;
            if (element.matches("script, style, link, hr")) return;
            if (!element.matches(INTERACTIVE) && element.querySelector(".comfyui-button-group")) {
                for (const child of element.children) collect(child, scope);
                return;
            }
            if (element.matches(".comfyui-button-group")) {
                const groupScope = element.id ? `${scope}/${element.id}` : scope;
                for (const child of element.children) collect(child, groupScope);
                return;
            }
            if (seen.has(element) || (!element.matches(INTERACTIVE) && !element.textContent.trim() && !element.querySelector("svg, i, img, canvas"))) return;
            seen.add(element);
            let key = this.identities.get(element);
            const base = `${scope}/${identityOf(element)}`;
            const count = (counts.get(base) ?? 0) + 1;
            counts.set(base, count);
            if (!key) {
                key = `${base}/${count}`;
                this.identities.set(element, key);
            }
            element.toggleAttribute(HIDDEN_ATTRIBUTE, this.hidden.has(key));
            entries.push({ key, element, label: textOf(element) || identityOf(element), scope });
        };
        for (const [root, scope] of currentRoots) {
            for (const child of root.children) collect(child, scope);
            for (const group of root.querySelectorAll(".comfyui-button-group")) {
                const children = [...group.children];
                group.toggleAttribute("data-cd-toolbar-empty", children.some(child => child.hasAttribute(HIDDEN_ATTRIBUTE)) &&
                    children.every(child => child.hasAttribute(HIDDEN_ATTRIBUTE) || getComputedStyle(child).display === "none"));
            }
        }
        // Drop our markers from elements moved out of the managed toolbar.
        for (const entry of this.entries) {
            if (!seen.has(entry.element)) {
                entry.element.removeAttribute(HIDDEN_ATTRIBUTE);
                entry.element.closest("[data-cd-toolbar-empty]")?.removeAttribute("data-cd-toolbar-empty");
            }
        }
        this.entries = entries;
        if (this.dialog?.open) this.renderRows();
    }

    save() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify([...this.hidden]));
            this.saveError = false;
        } catch {
            this.saveError = true;
        }
        this.scan();
    }

    show() {
        if (!this.dialog) this.createDialog();
        if (!this.dialog.open) this.dialog.showModal();
        this.scan();
        this.searchInput.focus();
    }

    createDialog() {
        const dialog = document.createElement("dialog");
        dialog.className = "cd-toolbar-dialog";
        dialog.setAttribute("aria-labelledby", "cd-toolbar-title");
        const heading = document.createElement("h2");
        heading.id = "cd-toolbar-title";
        heading.textContent = "顶部工具栏管理";
        const description = document.createElement("p");
        description.textContent = "取消勾选即可隐藏。显示设置只影响当前浏览器，不会停用插件；插件自身关闭的元素不会被强制显示。";
        const search = document.createElement("input");
        search.type = "search";
        search.placeholder = "搜索工具栏元素…";
        search.setAttribute("aria-label", "搜索工具栏元素");
        search.addEventListener("input", () => {
            this.search = search.value.trim().toLowerCase();
            this.renderRows();
        });
        const rows = document.createElement("div");
        rows.className = "cd-toolbar-rows";
        const status = document.createElement("p");
        status.className = "cd-toolbar-status";
        status.setAttribute("role", "status");
        const actions = document.createElement("div");
        actions.className = "cd-toolbar-actions";
        for (const [label, action] of [
            ["重新扫描", () => this.scan()],
            ["恢复全部显示", () => { this.hidden.clear(); this.save(); }],
            ["关闭", () => dialog.close()],
        ]) {
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = label;
            button.addEventListener("click", action);
            actions.append(button);
        }
        dialog.append(heading, description, search, rows, status, actions);
        document.body.append(dialog);
        this.dialog = dialog;
        this.rows = rows;
        this.status = status;
        this.searchInput = search;
    }

    renderRows() {
        const rows = [];
        const focusedKey = this.rows.contains(document.activeElement) ? document.activeElement.dataset.key : null;
        let focusTarget;
        const detected = new Set(this.entries.map(entry => entry.key));
        const entries = [...this.entries];
        for (const key of this.hidden) {
            if (!detected.has(key)) entries.push({ key, label: key, scope: "当前未检测到（保留的隐藏规则）" });
        }
        for (const entry of entries) {
            if (this.search && !`${entry.label} ${entry.key}`.toLowerCase().includes(this.search)) continue;
            const row = document.createElement("label");
            row.className = "cd-toolbar-row";
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.dataset.key = entry.key;
            checkbox.checked = !this.hidden.has(entry.key);
            if (focusedKey === entry.key) focusTarget = checkbox;
            checkbox.addEventListener("change", () => {
                if (checkbox.checked) this.hidden.delete(entry.key);
                else this.hidden.add(entry.key);
                this.save();
            });
            const text = document.createElement("span");
            const name = document.createElement("span");
            name.className = "cd-toolbar-name";
            name.textContent = entry.label;
            const detail = document.createElement("small");
            detail.textContent = entry.element ? entry.key : entry.scope;
            text.append(name, detail);
            row.append(checkbox, text);
            rows.push(row);
        }
        if (!rows.length) {
            const empty = document.createElement("p");
            empty.textContent = this.search ? "没有匹配的元素。" : "尚未检测到插件工具栏元素，可在插件加载完成后重新扫描。";
            rows.push(empty);
        }
        this.rows.replaceChildren(...rows);
        focusTarget?.focus({ preventScroll: true });
        this.status.textContent = this.saveError
            ? "当前浏览器禁止保存配置，本次修改刷新后可能丢失。"
            : `检测到 ${this.entries.length} 项，已保存 ${this.hidden.size} 条隐藏规则。修改立即生效。`;
    }
}

let manager;
app.registerExtension({
    name: "CDToolSets.ToolbarManager",
    commands: [{
        id: COMMAND,
        label: "顶部工具栏管理",
        menubarLabel: "顶部工具栏管理",
        function: () => manager?.show(),
    }],
    menuCommands: [{ path: ["CDToolSets"], commands: [COMMAND] }],
    setup() {
        manager = new ToolbarManager();
        manager.start();
    },
});
