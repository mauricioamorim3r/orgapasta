"""Persistence helpers for local menu history."""

import json
import os
import threading
from datetime import datetime, timezone


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'menus_db.json')
LOCK = threading.Lock()
DEFAULT_DB = {'version': 1, 'menus': []}


def _ensure_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if not os.path.exists(DB_PATH):
        with open(DB_PATH, 'w', encoding='utf-8') as file_handle:
            json.dump(DEFAULT_DB, file_handle, indent=2, ensure_ascii=False)


def _load_db() -> dict:
    with LOCK:
        _ensure_db()
        try:
            with open(DB_PATH, 'r', encoding='utf-8') as file_handle:
                return json.load(file_handle)
        except (json.JSONDecodeError, OSError):
            return dict(DEFAULT_DB)


def _save_db(data: dict) -> None:
    with LOCK:
        with open(DB_PATH, 'w', encoding='utf-8') as file_handle:
            json.dump(data, file_handle, indent=2, ensure_ascii=False)


def db_get_all(page: int = 1, per_page: int = 20, q: str = '') -> dict:
    db = _load_db()
    menus = [menu for menu in db.get('menus', []) if menu.get('saved_to_history', True)]
    if q:
        query_lower = q.lower()
        menus = [menu for menu in menus if query_lower in menu.get('restaurant_name', '').lower()]

    menus_sorted = sorted(menus, key=lambda menu: menu.get('analyzed_at', ''), reverse=True)
    total = len(menus_sorted)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = menus_sorted[start:end]

    summaries = []
    for menu in page_items:
        summaries.append({
            'menu_id': menu.get('menu_id'),
            'restaurant_name': menu.get('restaurant_name', 'Sem nome'),
            'analyzed_at': menu.get('analyzed_at'),
            'location_notes': menu.get('location_notes', ''),
            'price_range': menu.get('price_range', ''),
            'total_items': menu.get('summary', {}).get('total_items', 0),
            'photo_count': menu.get('photo_count', 1),
            'provider': menu.get('provider', 'claude'),
            'cover_image': (menu.get('photo_files') or [{}])[0].get('url', ''),
            'cuisine_hints': menu.get('summary', {}).get('cuisine_hints', []),
        })

    return {'ok': True, 'total': total, 'page': page, 'per_page': per_page, 'menus': summaries}


def db_get_one(menu_id: str) -> dict | None:
    db = _load_db()
    for menu in db.get('menus', []):
        if menu.get('menu_id') == menu_id:
            return menu
    return None


def db_save_menu(record: dict) -> None:
    db = _load_db()
    menus = [menu for menu in db.get('menus', []) if menu.get('menu_id') != record['menu_id']]
    menus.append(record)
    db['menus'] = menus
    _save_db(db)


def db_delete_menu(menu_id: str) -> bool:
    db = _load_db()
    menus = db.get('menus', [])
    new_menus = [menu for menu in menus if menu.get('menu_id') != menu_id]
    if len(new_menus) == len(menus):
        return False
    db['menus'] = new_menus
    _save_db(db)
    return True


def build_menu_record(
    menu_id: str,
    restaurant_name: str,
    location_notes: str,
    analysis: dict,
    photo_count: int,
    provider: str,
    model_used: str,
    photo_files: list[dict],
    saved_to_history: bool,
) -> dict:
    summary = analysis.get('summary', {})
    return {
        'menu_id': menu_id,
        'restaurant_name': restaurant_name or 'Restaurante sem nome',
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
        'location_notes': location_notes or '',
        'photo_count': photo_count,
        'provider': provider,
        'model_used': model_used,
        'saved_to_history': saved_to_history,
        'photo_files': photo_files,
        'price_range': summary.get('price_range', ''),
        'categories': analysis.get('categories', []),
        'summary': summary,
        'raw_analysis': analysis.get('raw_analysis', ''),
    }