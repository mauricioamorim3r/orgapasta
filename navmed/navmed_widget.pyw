"""
NavMed — Widget Autônomo
========================
Roda SEM o Flask. Lê config.json diretamente.
Inicia com o Windows via registro.

Modos:
  panel  — painel vertical (favoritos + recentes)
  grid   — grade de ícones estilo iOS
  mini   — ícone flutuante compacto (48 x 48 px)

Atalhos no header (botão direito):
  • Alternar modo
  • Iniciar com Windows (on/off)
  • Abrir app principal (NavMed Flask)
  • Ocultar / Fechar

Uso:
  pythonw navmed_widget.pyw     ← sem janela de console
  python  navmed_widget.pyw     ← com console (debug)
"""

import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import Menu, messagebox
import webbrowser
import winreg

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
APP_PY      = os.path.join(SCRIPT_DIR, "app.py")
APP_URL     = "http://localhost:5200"
REG_KEY     = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_NAME    = "NavMed"

# ── Colors ────────────────────────────────────────────────────────────────────
BG         = "#1a2035"
HEADER_BG  = "#1e2944"
MINI_BG    = "#1e2944"
FG_WHITE   = "#ffffff"
FG_YELLOW  = "#eab308"
FG_GRAY    = "#64748b"
FG_ITEM    = "#e2e8f0"
FG_BLUE    = "#3b82f6"
FG_RED     = "#ef4444"
ICON_BG    = "#243155"
ICON_HOV   = "#2d3f6e"
ICON_SEP   = "#2a3a5c"

# ── Modos ─────────────────────────────────────────────────────────────────────
MODE_PANEL = "panel"
MODE_GRID  = "grid"
MODE_MINI  = "mini"

MODE_ICONS = {MODE_PANEL: "☰", MODE_GRID: "⊞", MODE_MINI: "◉"}
MODE_LABEL = {MODE_PANEL: "Painel", MODE_GRID: "Grade iOS", MODE_MINI: "Mini ícone"}

# ── Tamanhos por modo ─────────────────────────────────────────────────────────
SIZES = {
    MODE_PANEL: (230, 420),
    MODE_GRID:  (270, 330),
    MODE_MINI:  (52,  52),
}
MIN_PANEL = (200, 280)

ALPHA_SHOW = 0.96
ALPHA_HIDE = 0.05
REFRESH_MS = 5000


# ═════════════════════════════════════════════════════════════════════════════
#  Config helpers
# ═════════════════════════════════════════════════════════════════════════════

def _load_config() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"[NavMed] Erro ao salvar config: {exc}")


def _flatten_tree(nodes: list) -> dict:
    index = {}
    def _walk(items):
        for item in items:
            iid = item.get("id")
            if iid:
                index[iid] = item
            _walk(item.get("children", []))
    _walk(nodes)
    return index


def _open_path(path: str):
    """Abre pasta de rede, URL ou diretório local."""
    if not path:
        return
    try:
        if path.startswith("http://") or path.startswith("https://"):
            webbrowser.open(path)
        elif path.startswith("\\\\") or (len(path) > 1 and path[1] == ":"):
            os.startfile(path)
        else:
            webbrowser.open(path)
    except Exception as exc:
        print(f"[NavMed] Erro ao abrir: {path} → {exc}")


# ═════════════════════════════════════════════════════════════════════════════
#  Windows Startup (registro)
# ═════════════════════════════════════════════════════════════════════════════

def _get_startup_cmd() -> str:
    """Comando para iniciar o widget sem console."""
    pyexe = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pyexe):
        pyexe = sys.executable   # fallback
    script = os.path.abspath(__file__)
    return f'"{pyexe}" "{script}"'


def _is_in_startup() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, REG_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _add_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, _get_startup_cmd())
        winreg.CloseKey(key)
        return True
    except Exception as exc:
        print(f"[NavMed] Erro no registro: {exc}")
        return False


def _remove_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, REG_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ═════════════════════════════════════════════════════════════════════════════
#  App principal
# ═════════════════════════════════════════════════════════════════════════════

def _launch_main_app():
    """Abre o NavMed principal em background (Flask)."""
    try:
        import requests
        requests.get(APP_URL, timeout=1)
        webbrowser.open(APP_URL)   # já rodando
    except Exception:
        try:
            subprocess.Popen(
                [sys.executable, APP_PY],
                cwd=SCRIPT_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            time.sleep(2)
            webbrowser.open(APP_URL)
        except Exception as exc:
            messagebox.showerror("NavMed", f"Não foi possível abrir o app:\n{exc}")


# ═════════════════════════════════════════════════════════════════════════════
#  Widget principal
# ═════════════════════════════════════════════════════════════════════════════

class NavMedWidget:
    def __init__(self):
        self._cfg   = _load_config()
        self._mtime = self._get_mtime()
        self._mode  = self._cfg.get("widget", {}).get("mode", MODE_PANEL)
        self._drag  = {"x": 0, "y": 0, "active": False}
        self._resize = {"active": False, "x": 0, "y": 0, "w": 0, "h": 0}
        self._expanded = True   # para modo mini: True = painel expandido aberto

        self.root = tk.Tk()
        self.root.withdraw()   # esconde enquanto constrói

        self._apply_window_base()
        self._build()

        self.root.deiconify()
        self.root.after(REFRESH_MS, self._poll_config)
        self.root.mainloop()

    # ── Config mtime ─────────────────────────────────────────────────────────
    def _get_mtime(self) -> float:
        try:
            return os.path.getmtime(CONFIG_FILE)
        except Exception:
            return 0.0

    # ── Janela base ───────────────────────────────────────────────────────────
    def _apply_window_base(self):
        r = self.root
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.attributes("-alpha", ALPHA_HIDE)
        r.configure(bg=BG)

        wcfg = self._cfg.get("widget", {})
        x = wcfg.get("x", 80)
        y = wcfg.get("y", 80)
        w, h = SIZES.get(self._mode, SIZES[MODE_PANEL])
        w = max(wcfg.get("width",  w), MIN_PANEL[0]) if self._mode == MODE_PANEL else w
        h = max(wcfg.get("height", h), MIN_PANEL[1]) if self._mode == MODE_PANEL else h
        r.geometry(f"{w}x{h}+{x}+{y}")
        if self._mode == MODE_PANEL:
            r.minsize(*MIN_PANEL)
        else:
            r.minsize(1, 1)

        # hover transparency
        r.bind("<Enter>", lambda _: r.attributes("-alpha", ALPHA_SHOW))
        r.bind("<Leave>", lambda _: r.attributes("-alpha", ALPHA_HIDE))

        # drag
        r.bind("<ButtonPress-1>",   self._drag_start)
        r.bind("<B1-Motion>",       self._drag_move)
        r.bind("<ButtonRelease-1>", self._drag_end)

    # ── Drag ─────────────────────────────────────────────────────────────────
    def _drag_start(self, e):
        if self._resize["active"]:
            return
        self._drag["x"] = e.x_root - self.root.winfo_x()
        self._drag["y"] = e.y_root - self.root.winfo_y()
        self._drag["active"] = True

    def _drag_move(self, e):
        if not self._drag["active"] or self._resize["active"]:
            return
        self.root.geometry(f"+{e.x_root - self._drag['x']}+{e.y_root - self._drag['y']}")

    def _drag_end(self, _e):
        self._drag["active"] = False
        self._save_position()

    def _save_position(self):
        cfg = _load_config()
        w = cfg.setdefault("widget", {})
        w["x"] = self.root.winfo_x()
        w["y"] = self.root.winfo_y()
        if self._mode == MODE_PANEL:
            w["width"]  = self.root.winfo_width()
            w["height"] = self.root.winfo_height()
        _save_config(cfg)

    # ── Build / Rebuild ───────────────────────────────────────────────────────
    def _build(self):
        """Apaga tudo e reconstrói conforme o modo atual."""
        for w in self.root.winfo_children():
            w.destroy()

        if self._mode == MODE_MINI:
            self._build_mini()
        elif self._mode == MODE_GRID:
            self._build_grid()
        else:
            self._build_panel()

    def _rebuild(self, new_mode: str = None):
        """Troca de modo e reconstrói."""
        if new_mode:
            self._mode = new_mode
        w, h = SIZES.get(self._mode, SIZES[MODE_PANEL])
        cfg = _load_config()
        wcfg = cfg.get("widget", {})
        if self._mode == MODE_PANEL:
            w = max(wcfg.get("width",  w), MIN_PANEL[0])
            h = max(wcfg.get("height", h), MIN_PANEL[1])
        x = wcfg.get("x", self.root.winfo_x())
        y = wcfg.get("y", self.root.winfo_y())
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        if self._mode == MODE_PANEL:
            self.root.minsize(*MIN_PANEL)
        else:
            self.root.minsize(1, 1)
        # salva modo
        cfg.setdefault("widget", {})["mode"] = self._mode
        _save_config(cfg)
        self._cfg = cfg
        self._build()

    # ─────────────────────────────────────────────────────────────────────────
    #  MODO PAINEL
    # ─────────────────────────────────────────────────────────────────────────
    def _build_panel(self):
        self._add_header()

        content = tk.Frame(self.root, bg=BG)
        content.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 0))

        # Favoritos
        tk.Label(content, text="⭐  Favoritos", fg=FG_YELLOW, bg=BG,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(fill=tk.X, padx=4, pady=(4, 0))

        self._fav_frame = tk.Frame(content, bg=BG)
        self._fav_frame.pack(fill=tk.X)

        tk.Frame(content, bg=ICON_SEP, height=1).pack(fill=tk.X, padx=8, pady=4)

        # Recentes
        tk.Label(content, text="🕐  Recentes", fg=FG_GRAY, bg=BG,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(fill=tk.X, padx=4)

        self._rec_frame = tk.Frame(content, bg=BG)
        self._rec_frame.pack(fill=tk.X)

        # Resize handle
        rh = tk.Label(self.root, text="⠿", fg=FG_GRAY, bg=BG,
                      font=("Segoe UI", 8), cursor="size_nw_se")
        rh.pack(side=tk.BOTTOM, anchor="se", padx=2)
        rh.bind("<ButtonPress-1>",   self._res_start)
        rh.bind("<B1-Motion>",       self._res_move)
        rh.bind("<ButtonRelease-1>", self._res_end)

        self._populate_panel()

    def _populate_panel(self):
        flat   = _flatten_tree(self._cfg.get("tree", []))
        recent = self._cfg.get("recent", [])
        favs   = [n for n in flat.values() if n.get("pinned")]

        for f in self._fav_frame.winfo_children():
            f.destroy()
        for f in self._rec_frame.winfo_children():
            f.destroy()

        if favs:
            for node in favs:
                self._panel_btn(self._fav_frame, node)
        else:
            tk.Label(self._fav_frame, text="  Nenhum favorito", fg=FG_GRAY, bg=BG,
                     font=("Segoe UI", 8), anchor="w").pack(fill=tk.X, padx=4)

        shown = 0
        for rid in recent:
            node = flat.get(rid)
            if node:
                self._panel_btn(self._rec_frame, node)
                shown += 1
                if shown >= 6:
                    break
        if shown == 0:
            tk.Label(self._rec_frame, text="  Nenhum recente", fg=FG_GRAY, bg=BG,
                     font=("Segoe UI", 8), anchor="w").pack(fill=tk.X, padx=4)

    def _panel_btn(self, parent: tk.Frame, item: dict):
        icon  = item.get("icon", "📁")
        label = item.get("label", item.get("name", "?"))
        text  = f"{icon}  {label[:22]}" if len(label) > 22 else f"{icon}  {label}"
        path  = item.get("path", item.get("url", ""))

        btn = tk.Button(
            parent, text=text, fg=FG_ITEM, bg=BG,
            relief=tk.FLAT, anchor="w", cursor="hand2",
            font=("Segoe UI", 8), bd=0, highlightthickness=0, pady=2,
            activebackground=ICON_HOV, activeforeground=FG_WHITE,
            command=lambda p=path: _open_path(p),
        )
        btn.pack(fill=tk.X, padx=6, pady=1)

    # ─────────────────────────────────────────────────────────────────────────
    #  MODO GRADE iOS
    # ─────────────────────────────────────────────────────────────────────────
    def _build_grid(self):
        self._add_header()

        flat   = _flatten_tree(self._cfg.get("tree", []))
        recent = self._cfg.get("recent", [])
        favs   = [n for n in flat.values() if n.get("pinned")]

        # combina favoritos + recentes (sem duplicatas)
        seen  = set()
        items = []
        for node in favs:
            nid = node.get("id")
            if nid not in seen:
                seen.add(nid)
                items.append(node)
        for rid in recent:
            node = flat.get(rid)
            if node and node.get("id") not in seen:
                seen.add(node["id"])
                items.append(node)
            if len(items) >= 15:
                break

        content = tk.Frame(self.root, bg=BG)
        content.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        if not items:
            tk.Label(content, text="Nenhum item\nconfigure no app ☰",
                     fg=FG_GRAY, bg=BG, font=("Segoe UI", 9),
                     justify="center").pack(expand=True)
            return

        COLS = 4
        for idx, node in enumerate(items):
            row = idx // COLS
            col = idx % COLS
            self._grid_icon(content, node, row, col)

    def _grid_icon(self, parent: tk.Frame, item: dict, row: int, col: int):
        icon  = item.get("icon", "📁")
        label = item.get("label", item.get("name", "?"))
        short = label[:8] + "…" if len(label) > 8 else label
        path  = item.get("path", item.get("url", ""))

        cell = tk.Frame(parent, bg=BG, width=58, height=64)
        cell.grid(row=row, column=col, padx=2, pady=2)
        cell.grid_propagate(False)

        # ícone (canvas com fundo arredondado simulado)
        cv = tk.Canvas(cell, width=44, height=44, bg=BG,
                       highlightthickness=0, cursor="hand2")
        cv.pack(pady=(2, 0))
        _draw_rounded_rect(cv, 2, 2, 42, 42, radius=10, fill=ICON_BG)
        cv.create_text(22, 22, text=icon, font=("Segoe UI Emoji", 16), fill=FG_WHITE)

        lbl = tk.Label(cell, text=short, fg=FG_GRAY, bg=BG,
                       font=("Segoe UI", 7), anchor="center", wraplength=56)
        lbl.pack()

        # hover + click
        def _enter(_):
            cv.delete("all")
            _draw_rounded_rect(cv, 2, 2, 42, 42, radius=10, fill=ICON_HOV)
            cv.create_text(22, 22, text=icon, font=("Segoe UI Emoji", 16), fill=FG_WHITE)
        def _leave(_):
            cv.delete("all")
            _draw_rounded_rect(cv, 2, 2, 42, 42, radius=10, fill=ICON_BG)
            cv.create_text(22, 22, text=icon, font=("Segoe UI Emoji", 16), fill=FG_WHITE)
        def _click(_):
            _open_path(path)

        for w in (cell, cv, lbl):
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)
            w.bind("<Button-1>", _click)
            w.configure(cursor="hand2")

    # ─────────────────────────────────────────────────────────────────────────
    #  MODO MINI
    # ─────────────────────────────────────────────────────────────────────────
    def _build_mini(self):
        """Ícone flutuante 52×52 px. Clique expande para painel pop-up."""
        cv = tk.Canvas(self.root, width=52, height=52, bg=MINI_BG,
                       highlightthickness=0, cursor="hand2")
        cv.pack()

        _draw_rounded_rect(cv, 2, 2, 50, 50, radius=14, fill=FG_BLUE)
        cv.create_text(26, 22, text="📂", font=("Segoe UI Emoji", 16), fill=FG_WHITE)
        cv.create_text(26, 40, text="Nav", font=("Segoe UI", 7, "bold"), fill=FG_WHITE)

        self._mini_popup = None

        def _click(_):
            if self._mini_popup and self._mini_popup.winfo_exists():
                self._mini_popup.destroy()
                self._mini_popup = None
            else:
                self._show_mini_popup()

        cv.bind("<Button-1>", _click)

        # botão direito = menu
        cv.bind("<Button-3>", self._show_menu)

        # hover hover override para mini
        cv.bind("<Enter>", lambda _: self.root.attributes("-alpha", ALPHA_SHOW))
        cv.bind("<Leave>", lambda _: self.root.attributes("-alpha", ALPHA_HIDE))

    def _show_mini_popup(self):
        """Abre um painel pop-up temporário ao lado do ícone mini."""
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()

        pop = tk.Toplevel(self.root)
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.configure(bg=BG)
        pop.geometry(f"220x360+{rx + 60}+{ry}")
        self._mini_popup = pop

        flat   = _flatten_tree(self._cfg.get("tree", []))
        recent = self._cfg.get("recent", [])
        favs   = [n for n in flat.values() if n.get("pinned")]

        # header mini-popup
        hdr = tk.Frame(pop, bg=HEADER_BG)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="📂 NavMed", fg=FG_WHITE, bg=HEADER_BG,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=6, pady=4)
        tk.Button(hdr, text="✕", fg=FG_RED, bg=HEADER_BG, relief=tk.FLAT,
                  bd=0, cursor="hand2", command=pop.destroy).pack(side=tk.RIGHT, padx=4)

        body = tk.Frame(pop, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        tk.Label(body, text="⭐ Favoritos", fg=FG_YELLOW, bg=BG,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(fill=tk.X, padx=4)
        for node in (favs or []):
            self._panel_btn(body, node)
        if not favs:
            tk.Label(body, text="  Nenhum favorito", fg=FG_GRAY, bg=BG,
                     font=("Segoe UI", 8)).pack(anchor="w", padx=8)

        tk.Frame(body, bg=ICON_SEP, height=1).pack(fill=tk.X, padx=8, pady=4)
        tk.Label(body, text="🕐 Recentes", fg=FG_GRAY, bg=BG,
                 font=("Segoe UI", 8, "bold"), anchor="w").pack(fill=tk.X, padx=4)
        shown = 0
        for rid in recent:
            node = flat.get(rid)
            if node:
                self._panel_btn(body, node)
                shown += 1
                if shown >= 5:
                    break
        if shown == 0:
            tk.Label(body, text="  Nenhum recente", fg=FG_GRAY, bg=BG,
                     font=("Segoe UI", 8)).pack(anchor="w", padx=8)

        # fecha ao clicar fora
        pop.bind("<FocusOut>", lambda _: pop.destroy())

    # ─────────────────────────────────────────────────────────────────────────
    #  Header (painel + grade)
    # ─────────────────────────────────────────────────────────────────────────
    def _add_header(self):
        hdr = tk.Frame(self.root, bg=HEADER_BG)
        hdr.pack(fill=tk.X)

        # ☰ abre app principal
        tk.Button(
            hdr, text="☰", fg=FG_BLUE, bg=HEADER_BG,
            relief=tk.FLAT, bd=0, cursor="hand2", padx=4, pady=3,
            activebackground=HEADER_BG,
            command=lambda: threading.Thread(target=_launch_main_app, daemon=True).start(),
        ).pack(side=tk.LEFT, padx=2)

        tk.Label(hdr, text="NavMed", fg=FG_WHITE, bg=HEADER_BG,
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, expand=True)

        # botão de modo (◉ ⊞ ☰)
        next_mode = {MODE_PANEL: MODE_GRID, MODE_GRID: MODE_MINI, MODE_MINI: MODE_PANEL}
        nxt = next_mode[self._mode]
        tk.Button(
            hdr, text=MODE_ICONS[nxt], fg=FG_GRAY, bg=HEADER_BG,
            relief=tk.FLAT, bd=0, cursor="hand2", padx=4, pady=3,
            activebackground=HEADER_BG,
            command=lambda m=nxt: self._rebuild(m),
        ).pack(side=tk.RIGHT, padx=2)

        # ✕ fecha
        tk.Button(
            hdr, text="✕", fg=FG_RED, bg=HEADER_BG,
            relief=tk.FLAT, bd=0, cursor="hand2", padx=4, pady=3,
            activebackground=HEADER_BG,
            command=self.root.destroy,
        ).pack(side=tk.RIGHT)

        # botão direito = menu
        hdr.bind("<Button-3>", self._show_menu)

    # ─────────────────────────────────────────────────────────────────────────
    #  Menu de contexto (botão direito)
    # ─────────────────────────────────────────────────────────────────────────
    def _show_menu(self, event):
        menu = Menu(self.root, tearoff=0,
                    bg=HEADER_BG, fg=FG_WHITE,
                    activebackground=ICON_HOV, activeforeground=FG_WHITE,
                    font=("Segoe UI", 9), relief=tk.FLAT, bd=0)

        menu.add_command(label="☰  Painel",    command=lambda: self._rebuild(MODE_PANEL))
        menu.add_command(label="⊞  Grade iOS", command=lambda: self._rebuild(MODE_GRID))
        menu.add_command(label="◉  Mini ícone", command=lambda: self._rebuild(MODE_MINI))
        menu.add_separator()

        if _is_in_startup():
            menu.add_command(label="✔  Iniciar com Windows (ativo)",
                             command=self._toggle_startup)
        else:
            menu.add_command(label="    Iniciar com Windows",
                             command=self._toggle_startup)

        menu.add_separator()
        menu.add_command(label="✎  Abrir NavMed (editar)",
                         command=lambda: threading.Thread(
                             target=_launch_main_app, daemon=True).start())
        menu.add_separator()
        menu.add_command(label="✕  Fechar widget", command=self.root.destroy)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _toggle_startup(self):
        if _is_in_startup():
            _remove_startup()
            messagebox.showinfo("NavMed", "Removido do início com o Windows.")
        else:
            if _add_startup():
                messagebox.showinfo("NavMed", "NavMed iniciará com o Windows!\n"
                                    "(Somente o widget, sem o app principal)")
            else:
                messagebox.showerror("NavMed", "Não foi possível adicionar ao registro.")

    # ─────────────────────────────────────────────────────────────────────────
    #  Resize (modo painel)
    # ─────────────────────────────────────────────────────────────────────────
    def _res_start(self, e):
        self._resize.update(active=True, x=e.x_root, y=e.y_root,
                            w=self.root.winfo_width(), h=self.root.winfo_height())
        self._drag["active"] = False

    def _res_move(self, e):
        if not self._resize["active"]:
            return
        dx = e.x_root - self._resize["x"]
        dy = e.y_root - self._resize["y"]
        nw = max(self._resize["w"] + dx, MIN_PANEL[0])
        nh = max(self._resize["h"] + dy, MIN_PANEL[1])
        self.root.geometry(f"{nw}x{nh}")

    def _res_end(self, _):
        self._resize["active"] = False
        self._save_position()

    # ─────────────────────────────────────────────────────────────────────────
    #  Poll config.json
    # ─────────────────────────────────────────────────────────────────────────
    def _poll_config(self):
        try:
            mtime = self._get_mtime()
            if mtime != self._mtime:
                self._mtime = mtime
                self._cfg = _load_config()
                if self._mode == MODE_PANEL:
                    self._populate_panel()
                else:
                    self._rebuild()
        except Exception:
            pass
        self.root.after(REFRESH_MS, self._poll_config)


# ═════════════════════════════════════════════════════════════════════════════
#  Canvas helper — retângulo arredondado
# ═════════════════════════════════════════════════════════════════════════════

def _draw_rounded_rect(canvas: tk.Canvas, x1, y1, x2, y2, radius=10, **kwargs):
    """Desenha um retângulo arredondado no canvas."""
    r = radius
    canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90,  extent=90,  style="pieslice", **kwargs)
    canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0,   extent=90,  style="pieslice", **kwargs)
    canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90,  style="pieslice", **kwargs)
    canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90,  style="pieslice", **kwargs)
    canvas.create_rectangle(x1+r, y1, x2-r, y2, **kwargs)
    canvas.create_rectangle(x1, y1+r, x2, y2-r, **kwargs)


# ═════════════════════════════════════════════════════════════════════════════
#  Ponto de entrada
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    NavMedWidget()
