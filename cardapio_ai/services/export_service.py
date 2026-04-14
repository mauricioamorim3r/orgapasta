"""HTML export generation for analyzed menus."""

import os


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
EXPORTS_DIR = os.path.join(BASE_DIR, 'exports')

ALLERGEN_LABELS = {
    'gluten': 'Gluten',
    'lactose': 'Lactose',
    'nuts': 'Nuts',
    'shellfish': 'Shellfish',
    'eggs': 'Eggs',
    'soy': 'Soy',
}

TAG_LABELS = {
    'vegetarian': 'Vegetarian',
    'vegan': 'Vegan',
}

BADGE_LABELS = {
    'best_value': 'Best value',
    'chefs_choice': 'Chef choice',
    'healthy_pick': 'Healthy pick',
    'popular_combo': 'Popular combo',
}


def get_export_path(menu_id: str) -> str:
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    return os.path.join(EXPORTS_DIR, f'{menu_id}.html')


def _format_currency(value) -> str:
    if value is None:
        return '-'
    return f'R$ {float(value):.2f}'.replace('.', ',')


def _render_highlights(summary: dict) -> str:
    highlights = summary.get('highlights', {})
    cards = []
    for key in ['best_value', 'chefs_choice', 'healthy_pick']:
        item = highlights.get(key)
        if item:
            cards.append(
                '<div class="highlight">'
                f'<div class="eyebrow">{BADGE_LABELS.get(key, key)}</div>'
                f'<div class="headline">{item.get("item_name", "")}</div>'
                '</div>'
            )

    combo = highlights.get('popular_combo', [])
    if combo and len(combo) >= 2:
        combo_names = ' + '.join(item.get('item_name', '') for item in combo[:2])
        cards.append(
            '<div class="highlight">'
            f'<div class="eyebrow">{BADGE_LABELS["popular_combo"]}</div>'
            f'<div class="headline">{combo_names}</div>'
            '</div>'
        )

    return ''.join(cards)


def _render_meta_chips(summary: dict) -> str:
    chips = []
    dietary_counts = summary.get('dietary_counts', {})
    allergen_counts = summary.get('allergen_counts', {})

    if dietary_counts.get('vegan'):
        chips.append(f'<span class="chip">Vegan: {dietary_counts["vegan"]}</span>')
    if dietary_counts.get('vegetarian'):
        chips.append(f'<span class="chip">Vegetarian: {dietary_counts["vegetarian"]}</span>')
    if dietary_counts.get('gluten_free'):
        chips.append(f'<span class="chip">Gluten free: {dietary_counts["gluten_free"]}</span>')

    if summary.get('detected_currency'):
        chips.append(f'<span class="chip">Currency: {summary["detected_currency"]}</span>')
    for language in summary.get('languages_detected', []):
        chips.append(f'<span class="chip">Language: {language}</span>')
    for cuisine in summary.get('cuisine_hints', []):
        chips.append(f'<span class="chip">Cuisine: {cuisine}</span>')

    for key, label in ALLERGEN_LABELS.items():
        if allergen_counts.get(key):
            chips.append(f'<span class="chip">{label}: {allergen_counts[key]}</span>')

    return ''.join(chips)


def _render_items(categories: list[dict]) -> str:
    parts = []
    for category in categories:
        items_html = []
        for item in category.get('items', []):
            tags = ''.join(
                f'<span class="token">{TAG_LABELS.get(tag, tag)}</span>' for tag in item.get('tags', [])
            )
            allergens = ''.join(
                f'<span class="token danger">{ALLERGEN_LABELS.get(allergen, allergen)}</span>'
                for allergen in item.get('allergens', [])
            )
            badges = ''.join(
                f'<span class="token">{BADGE_LABELS.get(badge, badge)}</span>'
                for badge in item.get('badges', [])
            )
            calories = item.get('calories_estimate')
            calories_html = f'<div class="mini">~{calories} kcal</div>' if calories else ''
            ingredients = ', '.join(item.get('ingredients_main', []))
            ingredients_html = f'<div class="mini">Ingredients: {ingredients}</div>' if ingredients else ''
            portion = item.get('portion_size', '')
            portion_html = f'<div class="mini">Portion: {portion}</div>' if portion else ''
            spice = item.get('spice_level', '')
            spice_html = f'<div class="mini">Spice: {spice}</div>' if spice and spice != 'unknown' else ''
            confidence = item.get('confidence')
            confidence_html = f'<div class="mini">Confidence: {round(float(confidence) * 100)}%</div>' if confidence is not None else ''
            items_html.append(
                '<div class="item">'
                '<div class="item-main">'
                f'<div class="item-name">{item.get("name", "")}</div>'
                f'<div class="item-desc">{item.get("description", "")}</div>'
                f'<div class="tokens">{tags}{allergens}{badges}</div>'
                '</div>'
                '<div class="item-side">'
                f'<div class="price">{item.get("price_raw") or _format_currency(item.get("price"))}</div>'
                f'{calories_html}'
                f'{ingredients_html}'
                f'{portion_html}'
                f'{spice_html}'
                f'{confidence_html}'
                '</div>'
                '</div>'
            )

        parts.append(
            '<section class="category">'
            f'<h2>{category.get("name", "Sem categoria")}</h2>'
            f'{"".join(items_html)}'
            '</section>'
        )

    return ''.join(parts)


def generate_export_html(menu: dict) -> str:
    summary = menu.get('summary', {})
    restaurant_name = menu.get('restaurant_name', 'Cardapio')
    location_notes = menu.get('location_notes', '')
    analyzed_at = menu.get('analyzed_at', '')[:10]
    raw_analysis = menu.get('raw_analysis', '')
    highlights_html = _render_highlights(summary)
    chips_html = _render_meta_chips(summary)
    items_html = _render_items(menu.get('categories', []))
    warnings_html = ''.join(f'<span class="chip">{warning}</span>' for warning in summary.get('warnings', []))
    photos_html = ''.join(
        f'<img src="{photo.get("url", "")}" alt="Foto do cardapio" class="photo">'
        for photo in menu.get('photo_files', [])
    )

    return f"""<!DOCTYPE html>
<html lang=\"pt-BR\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{restaurant_name} - Cardapio exportado</title>
  <style>
    :root {{
      --bg: #111111;
      --panel: #1d1b19;
      --line: #3d362f;
      --accent: #ff6b35;
      --text: #f7f2ea;
      --muted: #bea98c;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Georgia, serif; background: radial-gradient(circle at top, #30251c, var(--bg) 55%); color: var(--text); }}
    .wrap {{ max-width: 960px; margin: 0 auto; padding: 32px 18px 60px; }}
    .hero {{ border: 1px solid var(--line); border-radius: 24px; padding: 28px; background: rgba(29, 27, 25, 0.92); }}
    .eyebrow {{ color: var(--muted); text-transform: uppercase; letter-spacing: 0.2em; font-size: 12px; }}
    h1 {{ font-size: 42px; margin: 8px 0 4px; }}
    .sub {{ color: var(--muted); margin-bottom: 18px; }}
    .stats {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 18px; }}
    .stat {{ background: #171513; border: 1px solid var(--line); border-radius: 16px; padding: 12px 16px; min-width: 140px; }}
    .stat strong {{ display: block; font-size: 22px; margin-top: 4px; }}
    .chips {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 18px 0; }}
    .chip {{ border: 1px solid var(--line); border-radius: 999px; padding: 6px 10px; color: var(--muted); font-size: 12px; }}
    .highlights {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 22px 0 28px; }}
    .highlight {{ background: #171513; border: 1px solid var(--line); border-radius: 18px; padding: 16px; }}
    .headline {{ font-size: 20px; margin-top: 8px; }}
    .category {{ margin-top: 28px; border-top: 1px solid var(--line); padding-top: 24px; }}
    .category h2 {{ font-size: 28px; margin: 0 0 16px; }}
    .item {{ display: flex; justify-content: space-between; gap: 18px; padding: 14px 0; border-bottom: 1px solid rgba(61, 54, 47, 0.55); }}
    .item-name {{ font-size: 19px; font-weight: bold; }}
    .item-desc {{ color: var(--muted); margin-top: 4px; line-height: 1.5; }}
    .tokens {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .token {{ font-size: 11px; border: 1px solid var(--line); border-radius: 999px; padding: 4px 8px; }}
    .danger {{ color: #ffb29c; }}
    .item-side {{ text-align: right; min-width: 110px; }}
    .price {{ color: var(--accent); font-size: 22px; font-weight: bold; }}
    .mini {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
    .gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 22px; }}
    .photo {{ width: 100%; height: 180px; object-fit: cover; border-radius: 16px; border: 1px solid var(--line); }}
    .analysis {{ margin-top: 32px; padding: 20px; border-radius: 18px; background: rgba(29, 27, 25, 0.92); border: 1px solid var(--line); line-height: 1.7; }}
    @media (max-width: 700px) {{
      h1 {{ font-size: 32px; }}
      .item {{ flex-direction: column; }}
      .item-side {{ text-align: left; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <header class=\"hero\">
      <div class=\"eyebrow\">Cardapio AI export</div>
      <h1>{restaurant_name}</h1>
      <div class=\"sub\">{location_notes}</div>
      <div class=\"stats\">
        <div class=\"stat\">Itens<strong>{summary.get('total_items', 0)}</strong></div>
        <div class=\"stat\">Faixa<strong>{summary.get('price_range_label', '-')}</strong></div>
        <div class=\"stat\">Media<strong>{_format_currency(summary.get('price_avg'))}</strong></div>
        <div class=\"stat\">Data<strong>{analyzed_at or '-'}</strong></div>
      </div>
      <div class=\"chips\">{chips_html}</div>
            <div class=\"chips\">{warnings_html}</div>
    </header>
        <section class=\"gallery\">{photos_html}</section>
    <section class=\"highlights\">{highlights_html}</section>
    {items_html}
    <section class=\"analysis\">{raw_analysis}</section>
  </div>
</body>
</html>"""