"""Flask routes for Cardapio AI."""

import json
import os
import uuid

from flask import Blueprint, jsonify, request, send_file

from services.export_service import generate_export_html, get_export_path
from services.image_utils import UPLOADS_DIR, process_uploaded_images
from services.llm_service import PROVIDERS, call_llm_vision
from services.menu_repository import (
    build_menu_record,
    db_delete_menu,
    db_get_all,
    db_get_one,
    db_save_menu,
)


menu_bp = Blueprint('menu_bp', __name__)


@menu_bp.route('/api/menus/analyze', methods=['POST'])
def analyze_menu():
    files = request.files.getlist('photos[]')
    restaurant_name = request.form.get('restaurant_name', '').strip()
    location_notes = request.form.get('location_notes', '').strip()
    save_to_history = request.form.get('save', 'true').lower() == 'true'
    provider = request.form.get('provider', 'claude').strip().lower()
    if provider not in PROVIDERS:
        provider = 'claude'

    menu_id = str(uuid.uuid4())

    try:
        images, photo_files = process_uploaded_images(files, menu_id)
    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 422

    try:
        analysis, model_used = call_llm_vision(images, restaurant_name, provider)
    except RuntimeError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 503
    except json.JSONDecodeError as exc:
        return jsonify({'ok': False, 'error': f'Resposta invalida do modelo: {exc}'}), 500
    except Exception as exc:
        return jsonify({'ok': False, 'error': f'Erro na analise: {exc}'}), 500

    record = build_menu_record(
        menu_id=menu_id,
        restaurant_name=restaurant_name,
        location_notes=location_notes,
        analysis=analysis,
        photo_count=len(images),
        provider=provider,
        model_used=model_used,
        photo_files=photo_files,
        saved_to_history=save_to_history,
    )

    db_save_menu(record)

    return jsonify({'ok': True, **record})


@menu_bp.route('/api/menus/history', methods=['GET'])
def get_history():
    page = max(1, int(request.args.get('page', 1)))
    per_page = max(1, min(50, int(request.args.get('per_page', 20))))
    query = request.args.get('q', '')
    return jsonify(db_get_all(page=page, per_page=per_page, q=query))


@menu_bp.route('/api/menus/compare', methods=['GET'])
def compare_menus():
    menu_a_id = request.args.get('a', '')
    menu_b_id = request.args.get('b', '')
    if not menu_a_id or not menu_b_id:
        return jsonify({'ok': False, 'error': "Parametros 'a' e 'b' sao obrigatorios."}), 400

    menu_a = db_get_one(menu_a_id)
    menu_b = db_get_one(menu_b_id)
    if not menu_a:
        return jsonify({'ok': False, 'error': f"Cardapio '{menu_a_id}' nao encontrado."}), 404
    if not menu_b:
        return jsonify({'ok': False, 'error': f"Cardapio '{menu_b_id}' nao encontrado."}), 404

    def safe_float(value):
        return float(value) if value is not None else 0.0

    summary_a = menu_a.get('summary', {})
    summary_b = menu_b.get('summary', {})
    diff = {
        'price_avg_diff': round(safe_float(summary_a.get('price_avg')) - safe_float(summary_b.get('price_avg')), 2),
        'items_diff': summary_a.get('total_items', 0) - summary_b.get('total_items', 0),
        'vegan_diff': summary_a.get('dietary_counts', {}).get('vegan', 0) - summary_b.get('dietary_counts', {}).get('vegan', 0),
        'vegetarian_diff': summary_a.get('dietary_counts', {}).get('vegetarian', 0) - summary_b.get('dietary_counts', {}).get('vegetarian', 0),
    }

    return jsonify({'ok': True, 'a': menu_a, 'b': menu_b, 'diff': diff})


@menu_bp.route('/api/menus/<menu_id>', methods=['GET'])
def get_menu_detail(menu_id: str):
    menu = db_get_one(menu_id)
    if not menu:
        return jsonify({'ok': False, 'error': 'Cardapio nao encontrado.'}), 404
    return jsonify({'ok': True, **menu})


@menu_bp.route('/api/menus/<menu_id>', methods=['DELETE'])
def delete_menu(menu_id: str):
    if not db_delete_menu(menu_id):
        return jsonify({'ok': False, 'error': 'Cardapio nao encontrado.'}), 404

    export_path = get_export_path(menu_id)
    if os.path.exists(export_path):
        os.remove(export_path)

    upload_dir = os.path.join(UPLOADS_DIR, menu_id)
    if os.path.isdir(upload_dir):
        for name in os.listdir(upload_dir):
            os.remove(os.path.join(upload_dir, name))
        os.rmdir(upload_dir)

    return jsonify({'ok': True})


@menu_bp.route('/api/menus/<menu_id>/export', methods=['POST'])
def export_menu(menu_id: str):
    menu = db_get_one(menu_id)
    if not menu:
        return jsonify({'ok': False, 'error': 'Cardapio nao encontrado.'}), 404

    html_content = generate_export_html(menu)
    export_path = get_export_path(menu_id)
    with open(export_path, 'w', encoding='utf-8') as file_handle:
        file_handle.write(html_content)

    restaurant = menu.get('restaurant_name', 'Cardapio').replace(' ', '_')
    analyzed_at = menu.get('analyzed_at', '')[:10]
    return jsonify({
        'ok': True,
        'url': f'/api/menus/export/{menu_id}.html',
        'filename': f'{restaurant}_{analyzed_at}.html',
    })


@menu_bp.route('/api/menus/export/<filename>', methods=['GET'])
def serve_export(filename: str):
    safe_name = os.path.basename(filename)
    if not safe_name.endswith('.html'):
        return jsonify({'ok': False, 'error': 'Arquivo nao encontrado.'}), 404

    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'exports', safe_name)
    if not os.path.exists(file_path):
        return jsonify({'ok': False, 'error': 'Export nao encontrado. Gere novamente.'}), 404

    return send_file(file_path, mimetype='text/html')


@menu_bp.route('/api/uploads/<menu_id>/<filename>', methods=['GET'])
def serve_upload(menu_id: str, filename: str):
    safe_menu_id = os.path.basename(menu_id)
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(UPLOADS_DIR, safe_menu_id, safe_filename)
    if not os.path.exists(file_path):
        return jsonify({'ok': False, 'error': 'Imagem nao encontrada.'}), 404

    return send_file(file_path)