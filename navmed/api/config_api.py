"""
NavMed — Config API
====================
Handles reading/writing config.json with thread safety.

Endpoints:
  GET  /api/config  → returns full config as JSON
  POST /api/config  → saves JSON body, returns {"ok": true}
"""

import json
import os
import threading

from flask import Blueprint, jsonify, request

# ── Constants ─────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

_lock = threading.Lock()

DEFAULT_CONFIG = {
    "version": 1,
    "tree": [],
    "recent": [],
    "widget": {"x": 100, "y": 100, "width": 220, "height": 400},
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Read and return config dict; creates default config if file is missing."""
    with _lock:
        if not os.path.exists(CONFIG_PATH):
            _write_raw(DEFAULT_CONFIG)
            return dict(DEFAULT_CONFIG)
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            _write_raw(DEFAULT_CONFIG)
            return dict(DEFAULT_CONFIG)


def save_config(data: dict) -> None:
    """Write config dict to JSON with indent=2, under lock."""
    with _lock:
        _write_raw(data)


def _write_raw(data: dict) -> None:
    """Internal write — caller must hold lock or be in a safe context."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Blueprint ─────────────────────────────────────────────────────────────────
config_bp = Blueprint("config_bp", __name__)


@config_bp.route("/api/config", methods=["GET"])
def get_config():
    """Return full config as JSON."""
    return jsonify(load_config())


@config_bp.route("/api/config", methods=["POST"])
def post_config():
    """Receive JSON body, save it, return {"ok": true}."""
    data = request.get_json(force=True)
    if data is None:
        return jsonify({"ok": False, "error": "invalid JSON body"}), 400
    save_config(data)
    return jsonify({"ok": True})
