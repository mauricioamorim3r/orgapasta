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
import webbrowser

try:
    import requests
except ImportError:
    requests = None  # graceful degradation if not installed yet

API_BASE = "http://localhost:5200"
REFRESH_INTERVAL_MS = 5000


# ── Widget ─────────────────────────────────────────────────────────────────────

def run_widget():
    """Entry point called from daemon thread in app.py."""
    # Wait for Flask to be ready (retry until it responds)
    _wait_for_flask()

    root = tk.Tk()
    _build_widget(root)
    root.mainloop()


def _wait_for_flask(max_attempts: int = 20, delay: float = 1.0):
    """Block until Flask is accepting connections, with retries."""
    if requests is None:
        return
    for _ in range(max_attempts):
        try:
            requests.get(f"{API_BASE}/api/config", timeout=1)
            return
        except Exception:
            time.sleep(delay)


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

def _build_widget(root: tk.Tk):
    cfg = _fetch_config()
    widget_cfg = cfg.get("widget", {"x": 100, "y": 100, "width": 220, "height": 400})

    x = widget_cfg.get("x", 100)
    y = widget_cfg.get("y", 100)
    w = widget_cfg.get("width", 220)
    h = widget_cfg.get("height", 400)

    BG = "#1a2035"
    FG_WHITE  = "#ffffff"
    FG_YELLOW = "#f0c040"
    FG_GRAY   = "#9aa5c4"
    FG_ITEM   = "#c8d0e8"
    BTN_BG    = "#2a3250"

    # Window chrome
    root.title("NavMed")
    root.configure(bg=BG)
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.05)
    root.overrideredirect(True)

    # ── Drag support ──────────────────────────────────────────────────────────
    _drag = {"x": 0, "y": 0}

    def _on_press(event):
        _drag["x"] = event.x_root - root.winfo_x()
        _drag["y"] = event.y_root - root.winfo_y()

    def _on_drag(event):
        new_x = event.x_root - _drag["x"]
        new_y = event.y_root - _drag["y"]
        root.geometry(f"+{new_x}+{new_y}")

    def _on_release(event):
        # Save new position to config
        cfg = _fetch_config()
        wc = cfg.get("widget", {})
        wc["x"] = root.winfo_x()
        wc["y"] = root.winfo_y()
        cfg["widget"] = wc
        if requests is not None:
            try:
                requests.post(f"{API_BASE}/api/config", json=cfg, timeout=2)
            except Exception:
                pass

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

    # ── Main frame ────────────────────────────────────────────────────────────
    main_frame = tk.Frame(root, bg=BG)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    # Header
    header = tk.Frame(main_frame, bg=BG)
    header.pack(fill=tk.X)

    tk.Label(
        header, text="NavMed", fg=FG_WHITE, bg=BG,
        font=("Segoe UI", 10, "bold")
    ).pack(side=tk.LEFT, padx=4)

    tk.Button(
        header, text="☰", fg=FG_WHITE, bg=BTN_BG,
        relief=tk.FLAT, cursor="hand2", padx=4,
        command=lambda: webbrowser.open(f"{API_BASE}/")
    ).pack(side=tk.RIGHT, padx=2)

    tk.Button(
        header, text="✕", fg=FG_WHITE, bg=BTN_BG,
        relief=tk.FLAT, cursor="hand2", padx=4,
        command=root.destroy
    ).pack(side=tk.RIGHT, padx=2)

    # Separator
    tk.Frame(main_frame, bg="#3a4460", height=1).pack(fill=tk.X, pady=4)

    # Favorites section
    tk.Label(
        main_frame, text="⭐ Favoritos", fg=FG_YELLOW, bg=BG,
        font=("Segoe UI", 9, "bold"), anchor="w"
    ).pack(fill=tk.X, padx=4)

    fav_frame = tk.Frame(main_frame, bg=BG)
    fav_frame.pack(fill=tk.X, padx=4, pady=2)

    # Separator
    tk.Frame(main_frame, bg="#3a4460", height=1).pack(fill=tk.X, pady=4)

    # Recents section
    tk.Label(
        main_frame, text="🕐 Recentes", fg=FG_GRAY, bg=BG,
        font=("Segoe UI", 9, "bold"), anchor="w"
    ).pack(fill=tk.X, padx=4)

    rec_frame = tk.Frame(main_frame, bg=BG)
    rec_frame.pack(fill=tk.X, padx=4, pady=2)

    # ── Populate / refresh ────────────────────────────────────────────────────

    def _clear_frame(frame: tk.Frame):
        for child in frame.winfo_children():
            child.destroy()

    def _make_item_button(parent: tk.Frame, label: str, item_id: str, path: str):
        """Create a clickable item button."""
        text = label if len(label) <= 26 else label[:24] + "…"
        btn = tk.Button(
            parent, text=text, fg=FG_ITEM, bg=BTN_BG,
            relief=tk.FLAT, anchor="w", cursor="hand2",
            font=("Segoe UI", 8),
            command=lambda: _post_open(item_id, path),
        )
        btn.pack(fill=tk.X, pady=1)

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

    def refresh_data():
        cfg = _fetch_config()
        tree = cfg.get("tree", [])
        recent_ids = cfg.get("recent", [])
        flat = _flatten_tree(tree)

        # Favorites: items with pinned=True
        _clear_frame(fav_frame)
        favs = [node for node in flat.values() if node.get("pinned")]
        if favs:
            for node in favs:
                _make_item_button(
                    fav_frame,
                    node.get("label", node.get("name", "?")),
                    node.get("id", ""),
                    node.get("path", node.get("url", "")),
                )
        else:
            tk.Label(
                fav_frame, text="(nenhum)", fg=FG_GRAY, bg=BG,
                font=("Segoe UI", 8), anchor="w"
            ).pack(fill=tk.X)

        # Recents: look up recent ids in flat tree
        _clear_frame(rec_frame)
        shown = 0
        for rid in recent_ids:
            node = flat.get(rid)
            if node:
                _make_item_button(
                    rec_frame,
                    node.get("label", node.get("name", "?")),
                    node.get("id", ""),
                    node.get("path", node.get("url", "")),
                )
                shown += 1
                if shown >= 8:
                    break
        if shown == 0:
            tk.Label(
                rec_frame, text="(nenhum)", fg=FG_GRAY, bg=BG,
                font=("Segoe UI", 8), anchor="w"
            ).pack(fill=tk.X)

        # Schedule next refresh
        root.after(REFRESH_INTERVAL_MS, refresh_data)

    # Initial populate
    refresh_data()
