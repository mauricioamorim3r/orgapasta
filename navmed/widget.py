"""
NavMed — Floating tkinter Widget
==================================
Always-on-top, draggable, semi-transparent window that shows
pinned favorites and recent items from NavMed config.

Called from app.py in a daemon thread via run_widget().
"""

import threading
import time
import tkinter as tk
from tkinter import ttk
import webbrowser

try:
    import requests
except ImportError:
    requests = None  # graceful degradation if not installed yet

API_BASE = "http://localhost:5200"
REFRESH_INTERVAL_MS = 5000

# Minimum window dimensions
MIN_W = 200
MIN_H = 300

# ── Colors ──────────────────────────────────────────────────────────────────────
BG          = "#1a2035"
HEADER_BG   = "#1e2944"
FG_WHITE    = "#ffffff"
FG_YELLOW   = "#eab308"
FG_GRAY     = "#94a3b8"
FG_ITEM     = "#e2e8f0"
FG_BLUE     = "#3b82f6"
FG_RED      = "#ef4444"
ITEM_BTN_BG = "#1a2035"

# ── Widget ─────────────────────────────────────────────────────────────────────

def run_widget():
    """Entry point called from daemon thread in app.py."""
    root = tk.Tk()

    # _wait_for_flask blocks here; we are already in a daemon thread, so safe.
    flask_ok = _wait_for_flask(root)

    _build_widget(root, flask_ok=flask_ok)
    root.mainloop()


def _wait_for_flask(root: tk.Tk, max_attempts: int = 20, delay: float = 1.0) -> bool:
    """Block until Flask is accepting connections, with retries.
    Returns True if Flask was found, False otherwise."""
    if requests is None:
        return False
    for _ in range(max_attempts):
        try:
            requests.get(f"{API_BASE}/api/config", timeout=1)
            return True
        except Exception:
            time.sleep(delay)
    return False


def _show_error_label(parent: tk.Widget):
    """Display a prominent error label when Flask cannot be reached."""
    lbl = tk.Label(
        parent,
        text="⚠ Servidor\nnão encontrado",
        fg=FG_RED,
        bg=BG,
        font=("Segoe UI", 8),
        wraplength=180,
        justify="center",
    )
    lbl.pack(expand=True, fill=tk.BOTH, padx=8, pady=8)


def _fetch_config() -> dict:
    """Fetch config from Flask API. Returns empty dict on failure."""
    if requests is None:
        return {}
    try:
        resp = requests.get(f"{API_BASE}/api/config", timeout=2)
        if resp.ok:
            return resp.json()
    except Exception:
        pass
    return {}


def _post_open(item_id: str, path: str):
    """POST /api/open in a background thread to avoid blocking the UI."""
    if requests is None:
        return
    def _do():
        try:
            requests.post(
                f"{API_BASE}/api/open",
                json={"id": item_id, "path": path},
                timeout=3,
            )
        except Exception:
            pass
    threading.Thread(target=_do, daemon=True).start()


# ── Build UI ───────────────────────────────────────────────────────────────────

def _build_widget(root: tk.Tk, flask_ok: bool = True):
    cfg = _fetch_config() if flask_ok else {}
    widget_cfg = cfg.get("widget", {})

    x = widget_cfg.get("x", 100)
    y = widget_cfg.get("y", 100)
    w = max(widget_cfg.get("width",  220), MIN_W)
    h = max(widget_cfg.get("height", 400), MIN_H)

    # Window chrome
    root.title("NavMed")
    root.configure(bg=BG)
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.minsize(MIN_W, MIN_H)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.05)
    root.overrideredirect(True)

    # ── Drag support ──────────────────────────────────────────────────────────
    _drag = {"x": 0, "y": 0, "dragging": False}
    _resizing = {"active": False}

    def _on_press(event):
        if _resizing["active"]:
            return
        _drag["x"] = event.x_root - root.winfo_x()
        _drag["y"] = event.y_root - root.winfo_y()
        _drag["dragging"] = True

    def _on_drag(event):
        if not _drag["dragging"]:
            return
        new_x = event.x_root - _drag["x"]
        new_y = event.y_root - _drag["y"]
        root.geometry(f"+{new_x}+{new_y}")

    def _on_release(event):
        _drag["dragging"] = False
        # Save new position via the dedicated PATCH endpoint, in a daemon thread.
        if requests is None:
            return
        pos_x = root.winfo_x()
        pos_y = root.winfo_y()
        def _do():
            try:
                requests.patch(
                    f"{API_BASE}/api/config/widget-position",
                    json={"x": pos_x, "y": pos_y},
                    timeout=2,
                )
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    root.bind("<ButtonPress-1>", _on_press)
    root.bind("<B1-Motion>", _on_drag)
    root.bind("<ButtonRelease-1>", _on_release)

    # ── Hover transparency ────────────────────────────────────────────────────
    def _on_enter(_event):
        root.attributes("-alpha", 0.95)

    def _on_leave(_event):
        root.attributes("-alpha", 0.05)

    root.bind("<Enter>", _on_enter)
    root.bind("<Leave>", _on_leave)

    # ── Header bar ────────────────────────────────────────────────────────────
    header = tk.Frame(root, bg=HEADER_BG)
    header.pack(fill=tk.X)

    tk.Button(
        header, text="☰", fg=FG_BLUE, bg=HEADER_BG,
        relief=tk.FLAT, cursor="hand2", padx=4, pady=2,
        command=lambda: webbrowser.open(f"{API_BASE}/"),
        bd=0, highlightthickness=0,
    ).pack(side=tk.LEFT, padx=2)

    tk.Label(
        header, text="NavMed", fg=FG_WHITE, bg=HEADER_BG,
        font=("Segoe UI", 9, "bold"),
    ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

    tk.Button(
        header, text="✕", fg=FG_RED, bg=HEADER_BG,
        relief=tk.FLAT, cursor="hand2", padx=4, pady=2,
        command=root.destroy,
        bd=0, highlightthickness=0,
    ).pack(side=tk.RIGHT, padx=2)

    # ── Content area ──────────────────────────────────────────────────────────
    content = tk.Frame(root, bg=BG)
    content.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    # ── Error state ───────────────────────────────────────────────────────────
    if not flask_ok:
        _show_error_label(content)
        return

    # ── Favorites section ─────────────────────────────────────────────────────
    tk.Label(
        content, text="⭐ Favoritos", fg=FG_YELLOW, bg=BG,
        font=("Segoe UI", 8), anchor="w",
    ).pack(fill=tk.X, padx=4)

    fav_frame = tk.Frame(content, bg=BG)
    fav_frame.pack(fill=tk.X, padx=4, pady=2)

    # ── Separator ─────────────────────────────────────────────────────────────
    sep = ttk.Separator(content, orient="horizontal")
    sep.pack(fill=tk.X, pady=2)

    # ── Recents section ───────────────────────────────────────────────────────
    tk.Label(
        content, text="🕐 Recentes", fg=FG_GRAY, bg=BG,
        font=("Segoe UI", 8), anchor="w",
    ).pack(fill=tk.X, padx=4)

    rec_frame = tk.Frame(content, bg=BG)
    rec_frame.pack(fill=tk.X, padx=4, pady=2)

    # ── Resize handle (bottom-right corner) ───────────────────────────────────
    resize_handle = tk.Label(
        root, text="⠿", fg=FG_GRAY, bg=BG,
        font=("Segoe UI", 8), cursor="size_nw_se",
    )
    resize_handle.pack(side=tk.BOTTOM, anchor="se")

    _resize = {"x": 0, "y": 0}

    def _resize_press(event):
        _resizing["active"] = True
        _resize["x"] = event.x_root
        _resize["y"] = event.y_root
        _resize["w"] = root.winfo_width()
        _resize["h"] = root.winfo_height()

    def _resize_drag(event):
        dx = event.x_root - _resize["x"]
        dy = event.y_root - _resize["y"]
        new_w = max(_resize["w"] + dx, MIN_W)
        new_h = max(_resize["h"] + dy, MIN_H)
        root.geometry(f"{new_w}x{new_h}")

    def _resize_release(event):
        _resizing["active"] = False

    resize_handle.bind("<ButtonPress-1>", _resize_press)
    resize_handle.bind("<B1-Motion>", _resize_drag)
    resize_handle.bind("<ButtonRelease-1>", _resize_release)

    # ── Populate / refresh ────────────────────────────────────────────────────

    def _clear_frame(frame: tk.Frame):
        for child in frame.winfo_children():
            child.destroy()

    def _truncate(text: str, maxlen: int = 22) -> str:
        return text if len(text) <= maxlen else text[:maxlen] + "…"

    def _make_item_button(parent: tk.Frame, item: dict):
        """Create a clickable item button. Uses item=item default arg to avoid closure bugs."""
        icon  = item.get("icon", "")
        label = item.get("label", item.get("name", "?"))
        raw   = (f"{icon} {label}").strip() if icon else label
        text  = _truncate(raw, 22)
        item_id = item.get("id", "")
        path    = item.get("path", item.get("url", ""))
        btn = tk.Button(
            parent, text=text, fg=FG_ITEM, bg=ITEM_BTN_BG,
            relief=tk.FLAT, anchor="w", cursor="hand2",
            font=("Segoe UI", 8),
            bd=0, highlightthickness=0, pady=1,
            command=lambda item_id=item_id, path=path: _post_open(item_id, path),
        )
        btn.pack(fill=tk.X, padx=4, pady=1)

    def _flatten_tree(nodes: list) -> dict:
        """Return a flat dict of {id: node} for all items in the tree."""
        index = {}
        def _walk(items):
            for item in items:
                item_id = item.get("id")
                if item_id:
                    index[item_id] = item
                _walk(item.get("children", []))
        _walk(nodes)
        return index

    def _apply_config(cfg: dict):
        """Update widget UI from a fetched config dict. Must run on tkinter thread."""
        tree = cfg.get("tree", [])
        recent_ids = cfg.get("recent", [])
        flat = _flatten_tree(tree)

        # Favorites: items with pinned=True
        _clear_frame(fav_frame)
        favs = [node for node in flat.values() if node.get("pinned")]
        if favs:
            for node in favs:
                _make_item_button(fav_frame, node)
        else:
            tk.Label(
                fav_frame, text="Nenhum favorito", fg=FG_GRAY, bg=BG,
                font=("Segoe UI", 8), anchor="w",
            ).pack(fill=tk.X, padx=4)

        # Recents: look up recent ids in flat tree (max 5)
        _clear_frame(rec_frame)
        shown = 0
        for rid in recent_ids:
            node = flat.get(rid)
            if node:
                _make_item_button(rec_frame, node)
                shown += 1
                if shown >= 5:
                    break
        if shown == 0:
            tk.Label(
                rec_frame, text="Nenhum recente", fg=FG_GRAY, bg=BG,
                font=("Segoe UI", 8), anchor="w",
            ).pack(fill=tk.X, padx=4)

    def refresh_data():
        """Fetch config in a daemon thread, then apply results on the tkinter thread."""
        def _do_fetch():
            cfg = _fetch_config()
            if cfg:
                try:
                    root.after(0, lambda: _apply_config(cfg))
                except Exception:
                    pass  # window was destroyed
        threading.Thread(target=_do_fetch, daemon=True).start()
        root.after(REFRESH_INTERVAL_MS, refresh_data)

    # Initial populate using the config already fetched at startup
    try:
        root.after(0, lambda: _apply_config(cfg))
    except Exception:
        pass  # window was destroyed
    # Schedule periodic refresh
    root.after(REFRESH_INTERVAL_MS, refresh_data)
