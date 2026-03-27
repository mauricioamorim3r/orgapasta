"""
NavMed — Folders API
=====================
Handles folder opening, scanning, and creation.

Endpoints:
  POST /api/open   — open a path or URL
  GET  /api/scan   — scan a folder and return metadata
  POST /api/mkdir  — create a folder tree, optionally add to manager
"""

import os
import uuid
import webbrowser
from datetime import datetime

from flask import Blueprint, jsonify, request

from api.config_api import load_config, save_config

# ── Blueprint ─────────────────────────────────────────────────────────────────
folders_bp = Blueprint("folders_bp", __name__)


# ── POST /api/open ─────────────────────────────────────────────────────────────
@folders_bp.route("/api/open", methods=["POST"])
def open_path():
    """
    Body: {"id": "...", "path": "..."}
    Opens a local path or URL.
    Updates config["recent"] with item id (max 10).
    """
    try:
        body = request.get_json(force=True) or {}
        path = body.get("path", "").strip()
        item_id = body.get("id", "")

        if not path:
            return jsonify({"ok": False, "error": "path is required"}), 400

        # Determine how to open
        if path.startswith("http://") or path.startswith("https://"):
            webbrowser.open(path)
        elif path.startswith("\\\\") or (len(path) >= 3 and path[1] == ":" and path[2] in ("/", "\\")):
            os.startfile(path)
        else:
            # Attempt generic open for other paths
            os.startfile(path)

        # Update recent list
        if item_id:
            cfg = load_config()
            recent = cfg.get("recent", [])
            # Remove existing occurrence then prepend
            recent = [r for r in recent if r != item_id]
            recent.insert(0, item_id)
            cfg["recent"] = recent[:10]
            save_config(cfg)

        return jsonify({"ok": True})

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── GET /api/scan ──────────────────────────────────────────────────────────────
@folders_bp.route("/api/scan", methods=["GET"])
def scan_path():
    """
    Query param: ?path=...
    Scans top-level of folder + 1 level deep for file type counts.
    Returns metadata: file_count, dir_count, total_size_bytes, last_modified,
                      recent_files (top 5 by mtime), by_type.
    """
    path = request.args.get("path", "").strip()

    if not path:
        return jsonify({"ok": False, "error": "path query parameter is required"}), 400

    if not os.path.exists(path):
        return jsonify({"ok": False, "error": f"path does not exist: {path}"}), 404

    if not os.path.isdir(path):
        return jsonify({"ok": False, "error": f"path is not a directory: {path}"}), 400

    try:
        file_count = 0
        dir_count = 0
        total_size = 0
        all_files = []   # (mtime, name, size)
        by_type = {}

        def _process_entry(entry_path, name):
            nonlocal file_count, dir_count, total_size
            try:
                stat = os.stat(entry_path)
                if os.path.isfile(entry_path):
                    file_count += 1
                    size = stat.st_size
                    total_size += size
                    mtime = stat.st_mtime
                    all_files.append((mtime, name, size))
                    ext = os.path.splitext(name)[1].lstrip(".").lower()
                    if ext:
                        by_type[ext] = by_type.get(ext, 0) + 1
                elif os.path.isdir(entry_path):
                    dir_count += 1
            except PermissionError:
                pass

        # Top-level entries
        try:
            top_entries = os.scandir(path)
        except PermissionError:
            return jsonify({"ok": False, "error": "permission denied"}), 403

        subdirs = []
        with top_entries as it:
            for entry in it:
                _process_entry(entry.path, entry.name)
                if entry.is_dir(follow_symlinks=False):
                    subdirs.append(entry.path)

        # One level deep into subdirectories
        for subdir in subdirs:
            try:
                with os.scandir(subdir) as it2:
                    for entry in it2:
                        _process_entry(entry.path, entry.name)
            except PermissionError:
                pass

        # Sort files by mtime descending, take top 5
        all_files.sort(key=lambda x: x[0], reverse=True)
        recent_files = [
            {
                "name": name,
                "modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%dT%H:%M:%S"),
                "size_bytes": size,
            }
            for mtime, name, size in all_files[:5]
        ]

        # Last modified overall
        last_modified = ""
        if all_files:
            last_modified = datetime.fromtimestamp(all_files[0][0]).strftime("%Y-%m-%dT%H:%M:%S")

        return jsonify({
            "ok": True,
            "file_count": file_count,
            "dir_count": dir_count,
            "total_size_bytes": total_size,
            "last_modified": last_modified,
            "recent_files": recent_files,
            "by_type": by_type,
        })

    except PermissionError:
        return jsonify({"ok": False, "error": "permission denied"}), 403
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── POST /api/mkdir ────────────────────────────────────────────────────────────
@folders_bp.route("/api/mkdir", methods=["POST"])
def make_dirs():
    """
    Body: {"base_path": "...", "tree": [...], "add_to_manager": true}
    tree: [{"name": "FolderName", "children": [...]}]
    Creates folders recursively, reports per-path status.
    If add_to_manager is true, appends group to config["tree"].
    """
    try:
        body = request.get_json(force=True) or {}
        base_path = body.get("base_path", "").strip()
        tree = body.get("tree", [])
        add_to_manager = body.get("add_to_manager", False)

        if not base_path:
            return jsonify({"ok": False, "error": "base_path is required"}), 400

        results = []

        def _create_tree(parent_path: str, nodes: list) -> list:
            """Recursively create folders, return list of result dicts."""
            created_nodes = []
            for node in nodes:
                name = node.get("name", "").strip()
                if not name:
                    continue
                full_path = os.path.join(parent_path, name)
                try:
                    os.makedirs(full_path, exist_ok=True)
                    results.append({"path": full_path, "created": True, "error": None})
                    children = node.get("children", [])
                    child_nodes = _create_tree(full_path, children)
                    created_nodes.append({
                        "id": str(uuid.uuid4()),
                        "type": "folder",
                        "label": name,
                        "path": full_path,
                        "children": child_nodes,
                    })
                except PermissionError as pe:
                    results.append({"path": full_path, "created": False, "error": str(pe)})
                except Exception as exc:
                    results.append({"path": full_path, "created": False, "error": str(exc)})
            return created_nodes

        manager_nodes = _create_tree(base_path, tree)

        if add_to_manager and manager_nodes:
            cfg = load_config()
            group = {
                "id": str(uuid.uuid4()),
                "type": "group",
                "label": os.path.basename(base_path) or base_path,
                "children": manager_nodes,
            }
            cfg.setdefault("tree", []).append(group)
            save_config(cfg)

        return jsonify({"results": results})

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
