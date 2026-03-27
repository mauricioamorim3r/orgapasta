"""
NavMed — Flask Entrypoint
==========================
Serves the NavMed folder/link manager at http://localhost:5200
and launches the floating tkinter widget in a daemon thread.

Run:
    python app.py
    (or via navmed.bat for windowless start on Windows)
"""

import os
import subprocess
import sys
import threading
import time
import webbrowser
import winreg

from flask import Flask, jsonify, render_template

from api.config_api import config_bp
from api.folders import folders_bp

# ── Widget standalone paths ────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
WIDGET_SCRIPT = os.path.join(SCRIPT_DIR, "navmed_widget.pyw")
REG_KEY       = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_NAME      = "NavMed"

# ── App ────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
PORT = 5200

# Register blueprints
app.register_blueprint(config_bp)
app.register_blueprint(folders_bp)


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/creator")
def creator():
    return render_template("creator.html")


# ── Widget standalone API ──────────────────────────────────────────────────────

@app.route("/api/widget/launch", methods=["POST"])
def widget_launch():
    """Lança o widget autônomo como processo independente."""
    try:
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        subprocess.Popen(
            [pythonw, WIDGET_SCRIPT],
            cwd=SCRIPT_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return jsonify({"ok": True, "message": "Widget iniciado"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/widget/startup", methods=["POST"])
def widget_startup():
    """Alterna o widget no registro de inicialização do Windows."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0,
                             winreg.KEY_READ | winreg.KEY_SET_VALUE)
        try:
            winreg.QueryValueEx(key, REG_NAME)
            # já existe → remove
            winreg.DeleteValue(key, REG_NAME)
            winreg.CloseKey(key)
            return jsonify({"ok": True, "message": "Removido do início com Windows"})
        except FileNotFoundError:
            # não existe → adiciona
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(pythonw):
                pythonw = sys.executable
            cmd = f'"{pythonw}" "{WIDGET_SCRIPT}"'
            winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            return jsonify({"ok": True, "message": "✔ Iniciará com o Windows"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── Launch helpers ─────────────────────────────────────────────────────────────
def _open_browser():
    """Open the browser shortly after Flask starts."""
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{PORT}")


def _start_widget():
    """Import and run the tkinter widget (runs on its own thread)."""
    try:
        import widget
        widget.run_widget()
    except Exception as exc:
        # Widget failure must not crash Flask
        print(f"[NavMed] Widget error: {exc}")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  NavMed — Gerenciador de Pastas e Links")
    print(f"  http://localhost:{PORT}")
    print("=" * 50)

    # Start widget in daemon thread
    threading.Thread(target=_start_widget, daemon=True).start()

    # Open browser after short delay
    threading.Thread(target=_open_browser, daemon=True).start()

    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
