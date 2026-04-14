"""
NavMed — Flask Entrypoint
==========================
Serves the NavMed folder/link manager at http://localhost:5200
and launches the floating tkinter widget in a daemon thread.

Run:
    python app.py
    (or via navmed.bat for windowless start on Windows)
"""

import threading
import time
import webbrowser

from flask import Flask, render_template

from api.config_api import config_bp
from api.folders import folders_bp

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
