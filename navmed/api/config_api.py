"""
NavMed — Config API
====================
Handles reading/writing config.json with thread safety.

Endpoints:
  GET   /api/config                → returns full config as JSON
  POST  /api/config                → saves JSON body, returns {"ok": true}
  PATCH /api/config/widget-position → updates only widget x/y position
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
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
            return dict(DEFAULT_CONFIG)
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
            return dict(DEFAULT_CONFIG)


def save_config(data: dict) -> None:
    """Write config dict to JSON with indent=2, under lock."""
    with _lock:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def modify_config(fn) -> dict:
    """
    Atomically read-modify-write config.

    Acquires _lock, reads config, calls fn(config) to mutate in-place,
    writes the result back, and returns the modified config.
    """
    with _lock:
        if not os.path.exists(CONFIG_PATH):
            config = dict(DEFAULT_CONFIG)
        else:
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, OSError):
                config = dict(DEFAULT_CONFIG)
        fn(config)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    return config


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
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "payload must be a JSON object"}), 400
    save_config(data)
    return jsonify({"ok": True})


@config_bp.route("/api/config/widget-position", methods=["PATCH"])
def patch_widget_position():
    """Update only widget x/y position. Accepts {"x": int, "y": int}."""
    body = request.get_json(force=True)
    if not isinstance(body, dict):
        return jsonify({"ok": False, "error": "payload must be a JSON object"}), 400
    x = body.get("x")
    y = body.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        return jsonify({"ok": False, "error": "x and y must be integers"}), 400

    def _update(config):
        config.setdefault("widget", {})["x"] = x
        config["widget"]["y"] = y

    modify_config(_update)
    return jsonify({"ok": True})
