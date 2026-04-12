"""
NavMed — Menu Analyzer API
===========================
Analisa fotos de cardápios com múltiplos provedores de IA (Claude, GPT-4o, Gemini, Groq).
Retorna dados estruturados ricos: categorias, pratos, preços, nutrição, alérgenos, badges.

Endpoints:
  POST   /api/menus/analyze          → Upload de fotos + análise via LLM escolhido
  GET    /api/menus/history          → Lista menus salvos (paginado)
  GET    /api/menus/<menu_id>        → Detalhe de um menu
  DELETE /api/menus/<menu_id>        → Remove menu salvo
  POST   /api/menus/<menu_id>/export → Gera HTML exportável self-contained
  GET    /api/menus/export/<file>    → Serve arquivo HTML exportado
  GET    /api/menus/compare          → Compara dois menus (?a=<id>&b=<id>)
"""

import base64
import json
import os
import threading
import uuid
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv
from flask import Blueprint, jsonify, request, send_file

# ── Configuração ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY", "")
MENUS_DB_PATH = os.path.join(BASE_DIR, "menus_db.json")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

MAX_PHOTOS = 5
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

_db_lock = threading.Lock()

# ── System Prompt (cacheado no Claude) ───────────────────────────────────────
SYSTEM_PROMPT = """Você é um especialista em análise de cardápios de restaurantes com conhecimento profundo em nutrição, gastronomia e economia de alimentos. Quando receber fotos de um cardápio, realize uma análise estruturada e completa em 5 dimensões.

DIMENSÃO 1 — EXTRAÇÃO
Leia com precisão cada nome de prato, descrição e preço exatamente como impresso no cardápio.
Suporte múltiplas moedas, formatos de preço e idiomas.
Se um preço não estiver visível, use null.

DIMENSÃO 2 — CATEGORIZAÇÃO
Agrupe os pratos nas seções do cardápio (entradas, pratos principais, sobremesas, bebidas, etc.).
Se a seção não estiver rotulada, infira pelo tipo de prato.

DIMENSÃO 3 — INTELIGÊNCIA NUTRICIONAL
Estime calorias por porção com base no nome e descrição do prato (claramente marcado como estimativa).
Identifique alérgenos: gluten, lactose, nuts, shellfish, eggs, soy.
Marque pratos veganos (vegan) e vegetarianos (vegetarian).

DIMENSÃO 4 — INTELIGÊNCIA DE PREÇOS
Classifique a faixa de preço geral como: $, $$, $$$, ou $$$$.
Pontue cada prato com valor de 1 a 10 baseado na relação preço/porção e normas da categoria.
Calcule média, mínimo e máximo de preços dos itens com valor numérico.

DIMENSÃO 5 — RECOMENDAÇÕES INTELIGENTES
Atribua EXATAMENTE um prato para cada badge:
- "best_value": melhor pontuação de valor, preço razoável
- "chefs_choice": prato mais elaborado/distinto/especial do cardápio
- "healthy_pick": menores calorias, menos alérgenos, opção mais saudável
- "popular_combo": dois pratos que combinam bem juntos com bom preço combinado

FORMATO DE SAÍDA:
Responda SOMENTE com JSON válido seguindo EXATAMENTE este schema. Não inclua texto fora do JSON:

{
  "categories": [
    {
      "name": "nome da categoria",
      "items": [
        {
          "id": "uuid-gerado",
          "name": "nome do prato",
          "description": "descrição detalhada",
          "price": 22.90,
          "price_raw": "R$ 22,90",
          "calories_estimate": 350,
          "allergens": ["gluten"],
          "tags": ["vegetarian"],
          "badges": ["best_value"],
          "value_score": 8.5
        }
      ]
    }
  ],
  "summary": {
    "total_items": 24,
    "price_min": 18.0,
    "price_max": 89.0,
    "price_avg": 42.5,
    "price_range": "$$",
    "price_range_label": "Moderado ($$)",
    "highlights": {
      "best_value": {"item_id": "uuid", "item_name": "nome"},
      "chefs_choice": {"item_id": "uuid", "item_name": "nome"},
      "healthy_pick": {"item_id": "uuid", "item_name": "nome"},
      "popular_combo": [{"item_id": "uuid", "item_name": "nome"}, {"item_id": "uuid", "item_name": "nome"}]
    },
    "allergen_counts": {"gluten": 12, "lactose": 8, "nuts": 3, "shellfish": 2, "eggs": 5, "soy": 1},
    "dietary_counts": {"vegan": 4, "vegetarian": 9}
  },
  "raw_analysis": "Parágrafo narrativo descrevendo o cardápio, destaques e observações gerais."
}

Gere IDs UUID válidos para cada item. Seja preciso na extração e honesto nas estimativas."""

# ── Banco de dados thread-safe ────────────────────────────────────────────────

DEFAULT_DB = {"version": 1, "menus": []}


def _load_db() -> dict:
    with _db_lock:
        if not os.path.exists(MENUS_DB_PATH):
            with open(MENUS_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_DB, f, indent=2, ensure_ascii=False)
            return dict(DEFAULT_DB)
        try:
            with open(MENUS_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return dict(DEFAULT_DB)


def _save_db(data: dict) -> None:
    with _db_lock:
        with open(MENUS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def db_get_all(page: int = 1, per_page: int = 20, q: str = "") -> dict:
    db = _load_db()
    menus = db.get("menus", [])
    if q:
        q_lower = q.lower()
        menus = [m for m in menus if q_lower in m.get("restaurant_name", "").lower()]
    menus_sorted = sorted(menus, key=lambda m: m.get("analyzed_at", ""), reverse=True)
    total = len(menus_sorted)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = menus_sorted[start:end]
    # Retorna resumo (sem categories completas) para a listagem
    summaries = [
        {
            "menu_id": m.get("menu_id"),
            "restaurant_name": m.get("restaurant_name", "Sem nome"),
            "analyzed_at": m.get("analyzed_at"),
            "location_notes": m.get("location_notes", ""),
            "price_range": m.get("price_range", ""),
            "total_items": m.get("summary", {}).get("total_items", 0),
            "photo_count": m.get("photo_count", 1),
        }
        for m in page_items
    ]
    return {"ok": True, "total": total, "page": page, "per_page": per_page, "menus": summaries}


def db_get_one(menu_id: str) -> dict | None:
    db = _load_db()
    for m in db.get("menus", []):
        if m.get("menu_id") == menu_id:
            return m
    return None


def db_save_menu(record: dict) -> None:
    db = _load_db()
    menus = db.get("menus", [])
    menus = [m for m in menus if m.get("menu_id") != record["menu_id"]]
    menus.append(record)
    db["menus"] = menus
    _save_db(db)


def db_delete_menu(menu_id: str) -> bool:
    db = _load_db()
    menus = db.get("menus", [])
    new_menus = [m for m in menus if m.get("menu_id") != menu_id]
    if len(new_menus) == len(menus):
        return False
    db["menus"] = new_menus
    _save_db(db)
    return True


# ── Validação e processamento de imagens ─────────────────────────────────────

def validate_images(files) -> list:
    """Valida e retorna lista de (b64_str, mime_type)."""
    if not files:
        raise ValueError("Pelo menos uma foto é necessária.")
    if len(files) > MAX_PHOTOS:
        raise ValueError(f"Máximo de {MAX_PHOTOS} fotos permitidas.")
    result = []
    for f in files:
        mime = f.mimetype or ""
        if mime not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Tipo de imagem não suportado: {mime}. Use JPEG, PNG ou WebP.")
        data = f.read()
        if len(data) > MAX_SIZE_BYTES:
            raise ValueError(f"Imagem '{f.filename}' excede o limite de 5 MB.")
        b64 = base64.b64encode(data).decode("utf-8")
        result.append((b64, mime))
    return result


# ── Chamada ao Claude Vision ──────────────────────────────────────────────────

def call_claude_vision(images: list, restaurant_name: str) -> dict:
    """Envia imagens para Claude claude-sonnet-4-6 Vision e retorna análise estruturada."""
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "sua_chave_aqui":
        raise RuntimeError(
            "ANTHROPIC_API_KEY não configurada. "
            "Edite navmed/.env e adicione sua chave da Anthropic."
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Monta conteúdo: todas as imagens + texto
    content = []
    for b64_data, mime_type in images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": b64_data,
            },
        })
    content.append({
        "type": "text",
        "text": (
            f"Analise o cardápio do restaurante mostrado nas {len(images)} foto(s) acima.\n"
            f"Nome do restaurante (se conhecido): {restaurant_name or 'Desconhecido'}\n"
            "Retorne a análise completa em JSON conforme o schema definido."
        ),
    })

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # prompt caching
            }
        ],
        messages=[{"role": "user", "content": content}],
    )

    raw_text = response.content[0].text.strip()

    # Remove markdown fences se Claude envolver em ```json ... ```
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:])
        if raw_text.endswith("```"):
            raw_text = raw_text[: raw_text.rfind("```")]

    return json.loads(raw_text)


# ── Helper compartilhado ──────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    """Remove markdown code fences que alguns modelos inserem ao redor do JSON."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if "```" in text:
            text = text[: text.rfind("```")]
    return text.strip()


def _user_prompt(n_images: int, restaurant_name: str) -> str:
    return (
        f"Analise o cardápio do restaurante mostrado nas {n_images} foto(s) acima.\n"
        f"Nome do restaurante (se conhecido): {restaurant_name or 'Desconhecido'}\n"
        "Retorne a análise completa em JSON conforme o schema definido."
    )


# ── OpenAI Vision (GPT-4o) ────────────────────────────────────────────────────

def call_openai_vision(images: list, restaurant_name: str) -> dict:
    """Analisa cardápio via OpenAI GPT-4o Vision."""
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sua_chave_openai_aqui":
        raise RuntimeError(
            "OPENAI_API_KEY não configurada. "
            "Edite navmed/.env e adicione sua chave da OpenAI."
        )
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    content = []
    for b64_data, mime_type in images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{b64_data}",
                "detail": "high",
            },
        })
    content.append({"type": "text", "text": _user_prompt(len(images), restaurant_name)})

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
    )
    return json.loads(_strip_fences(response.choices[0].message.content))


# ── Google Gemini Vision (REST API — sem dependência extra) ───────────────────

def call_gemini_vision(images: list, restaurant_name: str) -> dict:
    """Analisa cardápio via Gemini 2.0 Flash REST API (urllib stdlib)."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "sua_chave_gemini_aqui":
        raise RuntimeError(
            "GEMINI_API_KEY não configurada. "
            "Edite navmed/.env e adicione sua chave do Google AI Studio."
        )
    import urllib.request as _req
    import urllib.error as _err

    parts = []
    for b64_data, mime_type in images:
        parts.append({"inline_data": {"mime_type": mime_type, "data": b64_data}})
    parts.append({"text": SYSTEM_PROMPT + "\n\n" + _user_prompt(len(images), restaurant_name)})

    payload = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"maxOutputTokens": 4096},
    }).encode("utf-8")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    )
    req = _req.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with _req.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
    except _err.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API erro {e.code}: {body[:200]}")

    raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(_strip_fences(raw_text))


# ── Groq Vision (Llama 4 Scout — gratuito) ───────────────────────────────────

def call_groq_vision(images: list, restaurant_name: str) -> dict:
    """Analisa cardápio via Groq Llama 4 Scout (gratuito com rate limits)."""
    if not GROQ_API_KEY or GROQ_API_KEY == "sua_chave_groq_aqui":
        raise RuntimeError(
            "GROQ_API_KEY não configurada. "
            "Crie uma chave gratuita em https://console.groq.com/ e edite navmed/.env."
        )
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

    content = []
    for b64_data, mime_type in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{b64_data}"},
        })
    content.append({
        "type": "text",
        "text": SYSTEM_PROMPT + "\n\n" + _user_prompt(len(images), restaurant_name),
    })

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": content}],
        max_tokens=4096,
    )
    return json.loads(_strip_fences(response.choices[0].message.content))


# ── Dispatch multi-provedor ───────────────────────────────────────────────────

PROVIDERS: dict[str, tuple[str, callable]] = {
    "claude": ("Claude Sonnet 4.6 · Anthropic", call_claude_vision),
    "openai": ("GPT-4o · OpenAI",               call_openai_vision),
    "gemini": ("Gemini 2.0 Flash · Google",      call_gemini_vision),
    "groq":   ("Llama 4 Scout · Groq",           call_groq_vision),
}


def call_llm_vision(images: list, restaurant_name: str, provider: str = "claude") -> tuple:
    """Despacha para o provedor selecionado. Retorna (analysis_dict, model_label)."""
    if provider not in PROVIDERS:
        provider = "claude"
    model_label, fn = PROVIDERS[provider]
    return fn(images, restaurant_name), model_label


# ── Construção do registro de menu ────────────────────────────────────────────

def build_menu_record(
    menu_id: str,
    restaurant_name: str,
    location_notes: str,
    analysis: dict,
    photo_count: int,
    provider: str = "claude",
    model_used: str = "",
) -> dict:
    summary = analysis.get("summary", {})
    return {
        "menu_id": menu_id,
        "restaurant_name": restaurant_name or "Restaurante sem nome",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "location_notes": location_notes or "",
        "photo_count": photo_count,
        "provider": provider,
        "model_used": model_used,
        "price_range": summary.get("price_range", ""),
        "categories": analysis.get("categories", []),
        "summary": summary,
        "raw_analysis": analysis.get("raw_analysis", ""),
    }


# ── Exportação HTML self-contained ────────────────────────────────────────────

ALLERGEN_ICONS = {
    "gluten": ("🌾", "Glúten"),
    "lactose": ("🥛", "Lactose"),
    "nuts": ("🥜", "Nozes"),
    "shellfish": ("🦐", "Frutos do mar"),
    "eggs": ("🥚", "Ovos"),
    "soy": ("🫘", "Soja"),
}

BADGE_LABELS = {
    "best_value": ("💰", "Melhor Custo-Benefício"),
    "chefs_choice": ("👨‍🍳", "Escolha do Chef"),
    "healthy_pick": ("🥗", "Opção Saudável"),
    "popular_combo": ("⭐", "Combo Popular"),
}


def _html_allergen_chips(allergens: list) -> str:
    chips = []
    for a in allergens:
        icon, label = ALLERGEN_ICONS.get(a, ("⚠️", a))
        chips.append(
            f'<span style="background:#7f1d1d;color:#fca5a5;padding:2px 6px;border-radius:4px;font-size:11px;margin:2px">'
            f"{icon} {label}</span>"
        )
    return "".join(chips)


def _html_tag_chips(tags: list) -> str:
    chips = []
    colors = {"vegetarian": ("#14532d", "#86efac"), "vegan": ("#064e3b", "#6ee7b7")}
    labels = {"vegetarian": "Vegetariano", "vegan": "Vegano"}
    for t in tags:
        bg, fg = colors.get(t, ("#1e3a5f", "#93c5fd"))
        label = labels.get(t, t)
        chips.append(
            f'<span style="background:{bg};color:{fg};padding:2px 6px;border-radius:4px;font-size:11px;margin:2px">'
            f"{label}</span>"
        )
    return "".join(chips)


def generate_export_html(menu: dict) -> str:
    """Gera HTML self-contained para exportação/compartilhamento."""
    name = menu.get("restaurant_name", "Cardápio")
    date_str = menu.get("analyzed_at", "")[:10]
    location = menu.get("location_notes", "")
    price_range = menu.get("price_range", "")
    summary = menu.get("summary", {})
    categories = menu.get("categories", [])
    raw = menu.get("raw_analysis", "")

    highlights = summary.get("highlights", {})
    allergen_counts = summary.get("allergen_counts", {})
    dietary_counts = summary.get("dietary_counts", {})
    price_min = summary.get("price_min")
    price_max = summary.get("price_max")
    price_avg = summary.get("price_avg")

    def fmt_price(v):
        if v is None:
            return "—"
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Highlights HTML
    highlights_html = ""
    for badge_key in ["best_value", "chefs_choice", "healthy_pick"]:
        h = highlights.get(badge_key, {})
        if h:
            icon, label = BADGE_LABELS.get(badge_key, ("", badge_key))
            highlights_html += (
                f'<div style="background:#1e3a5f;border:1px solid #3b82f6;border-radius:8px;padding:12px;flex:1;min-width:140px">'
                f'<div style="font-size:20px">{icon}</div>'
                f'<div style="color:#93c5fd;font-size:11px;margin-top:4px">{label}</div>'
                f'<div style="color:#e2e8f0;font-weight:bold;margin-top:4px">{h.get("item_name","")}</div>'
                f"</div>"
            )
    combo = highlights.get("popular_combo", [])
    if combo and len(combo) >= 2:
        icon, label = BADGE_LABELS["popular_combo"]
        names = " + ".join(c.get("item_name", "") for c in combo[:2])
        highlights_html += (
            f'<div style="background:#1e3a5f;border:1px solid #3b82f6;border-radius:8px;padding:12px;flex:1;min-width:140px">'
            f'<div style="font-size:20px">{icon}</div>'
            f'<div style="color:#93c5fd;font-size:11px;margin-top:4px">{label}</div>'
            f'<div style="color:#e2e8f0;font-weight:bold;margin-top:4px">{names}</div>'
            f"</div>"
        )

    # Categories HTML
    cats_html = ""
    for cat in categories:
        items_html = ""
        for item in cat.get("items", []):
            allergen_chips = _html_allergen_chips(item.get("allergens", []))
            tag_chips = _html_tag_chips(item.get("tags", []))
            cal = item.get("calories_estimate")
            cal_str = f"~{cal} kcal" if cal else ""
            price_str = item.get("price_raw") or fmt_price(item.get("price"))
            badges_html = ""
            for b in item.get("badges", []):
                icon, label = BADGE_LABELS.get(b, ("", b))
                badges_html += (
                    f'<span style="background:#1e3a5f;color:#93c5fd;padding:2px 6px;'
                    f'border-radius:4px;font-size:10px;margin:2px">{icon} {label}</span>'
                )
            items_html += (
                f'<tr style="border-bottom:1px solid #334155">'
                f'<td style="padding:10px 8px;vertical-align:top">'
                f'<div style="color:#e2e8f0;font-weight:600">{item.get("name","")}</div>'
                f'<div style="color:#94a3b8;font-size:12px;margin-top:2px">{item.get("description","")}</div>'
                f'<div style="margin-top:4px">{allergen_chips}{tag_chips}{badges_html}</div>'
                f'</td>'
                f'<td style="padding:10px 8px;text-align:right;vertical-align:top;white-space:nowrap">'
                f'<div style="color:#22c55e;font-weight:bold">{price_str}</div>'
                f'<div style="color:#94a3b8;font-size:11px;margin-top:2px">{cal_str}</div>'
                f'</td>'
                f'</tr>'
            )
        cats_html += (
            f'<div style="margin-bottom:24px">'
            f'<h3 style="color:#3b82f6;border-bottom:1px solid #334155;padding-bottom:8px;margin:0 0 12px">'
            f'{cat.get("name","")}</h3>'
            f'<table style="width:100%;border-collapse:collapse">{items_html}</table>'
            f"</div>"
        )

    # Allergen summary
    allergen_summary = ""
    for key, count in allergen_counts.items():
        if count > 0:
            icon, label = ALLERGEN_ICONS.get(key, ("⚠️", key))
            allergen_summary += (
                f'<span style="background:#7f1d1d;color:#fca5a5;padding:4px 10px;'
                f'border-radius:6px;margin:4px;display:inline-block;font-size:12px">'
                f"{icon} {label}: {count} pratos</span>"
            )

    diet_summary = ""
    if dietary_counts.get("vegan", 0):
        diet_summary += (
            f'<span style="background:#064e3b;color:#6ee7b7;padding:4px 10px;'
            f'border-radius:6px;margin:4px;display:inline-block;font-size:12px">'
            f"🌱 Veganos: {dietary_counts['vegan']}</span>"
        )
    if dietary_counts.get("vegetarian", 0):
        diet_summary += (
            f'<span style="background:#14532d;color:#86efac;padding:4px 10px;'
            f'border-radius:6px;margin:4px;display:inline-block;font-size:12px">'
            f"🥗 Vegetarianos: {dietary_counts['vegetarian']}</span>"
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="generator" content="NavMed Menu Analyzer">
<title>{name} — Cardápio Digital</title>
</head>
<body style="margin:0;padding:0;background:#0f1117;color:#e2e8f0;font-family:system-ui,sans-serif">
  <div style="max-width:900px;margin:0 auto;padding:24px 16px">

    <!-- Header -->
    <div style="text-align:center;margin-bottom:32px;border-bottom:2px solid #3b82f6;padding-bottom:24px">
      <div style="font-size:40px">🍽️</div>
      <h1 style="color:#e2e8f0;margin:8px 0 4px;font-size:28px">{name}</h1>
      {f'<div style="color:#94a3b8;font-size:14px">{location}</div>' if location else ""}
      <div style="display:flex;justify-content:center;gap:16px;margin-top:12px;flex-wrap:wrap">
        <span style="background:#1e3a5f;color:#93c5fd;padding:6px 14px;border-radius:20px;font-size:13px">
          {price_range} {summary.get("price_range_label","")}</span>
        <span style="background:#1a2035;color:#94a3b8;padding:6px 14px;border-radius:20px;font-size:13px">
          {summary.get("total_items",0)} pratos</span>
        <span style="background:#1a2035;color:#94a3b8;padding:6px 14px;border-radius:20px;font-size:13px">
          Analisado em {date_str}</span>
      </div>
    </div>

    <!-- Price Range -->
    <div style="background:#1a2035;border-radius:10px;padding:16px;margin-bottom:24px;display:flex;gap:24px;flex-wrap:wrap">
      <div style="text-align:center;flex:1">
        <div style="color:#94a3b8;font-size:12px">Mínimo</div>
        <div style="color:#22c55e;font-size:20px;font-weight:bold">{fmt_price(price_min)}</div>
      </div>
      <div style="text-align:center;flex:1">
        <div style="color:#94a3b8;font-size:12px">Média</div>
        <div style="color:#3b82f6;font-size:20px;font-weight:bold">{fmt_price(price_avg)}</div>
      </div>
      <div style="text-align:center;flex:1">
        <div style="color:#94a3b8;font-size:12px">Máximo</div>
        <div style="color:#ef4444;font-size:20px;font-weight:bold">{fmt_price(price_max)}</div>
      </div>
    </div>

    <!-- Highlights -->
    {f'<div style="margin-bottom:24px"><h2 style="color:#e2e8f0;margin:0 0 12px">Destaques</h2><div style="display:flex;gap:12px;flex-wrap:wrap">{highlights_html}</div></div>' if highlights_html else ""}

    <!-- Dietary & Allergens -->
    <div style="margin-bottom:24px">
      <div>{diet_summary}</div>
      <div style="margin-top:8px">{allergen_summary}</div>
    </div>

    <!-- Categories -->
    <div style="margin-bottom:32px">{cats_html}</div>

    <!-- Raw Analysis -->
    {f'<div style="background:#1a2035;border-radius:10px;padding:16px;margin-bottom:32px"><h3 style="color:#94a3b8;margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:1px">Análise Detalhada</h3><p style="color:#e2e8f0;line-height:1.6;margin:0">{raw}</p></div>' if raw else ""}

    <!-- Footer -->
    <div style="text-align:center;color:#334155;font-size:12px;border-top:1px solid #1e293b;padding-top:16px">
      Gerado por NavMed Menu Analyzer
    </div>
  </div>
</body>
</html>"""


def get_export_path(menu_id: str) -> str:
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    return os.path.join(EXPORTS_DIR, f"{menu_id}.html")


# ── Blueprint e rotas ─────────────────────────────────────────────────────────
menu_analyzer_bp = Blueprint("menu_analyzer_bp", __name__)


@menu_analyzer_bp.route("/api/menus/analyze", methods=["POST"])
def analyze_menu():
    """Upload de fotos + análise via LLM escolhido (claude/openai/gemini/groq)."""
    files = request.files.getlist("photos[]")
    restaurant_name = request.form.get("restaurant_name", "").strip()
    location_notes  = request.form.get("location_notes", "").strip()
    save_to_history = request.form.get("save", "true").lower() == "true"
    provider = request.form.get("provider", "claude").strip().lower()
    if provider not in PROVIDERS:
        provider = "claude"

    try:
        images = validate_images(files)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 422

    try:
        analysis, model_used = call_llm_vision(images, restaurant_name, provider)
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e)}), 503
    except json.JSONDecodeError as e:
        return jsonify({"ok": False, "error": f"O modelo retornou resposta inválida: {e}"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": f"Erro na análise: {e}"}), 500

    menu_id = str(uuid.uuid4())
    record = build_menu_record(
        menu_id, restaurant_name, location_notes, analysis, len(images), provider, model_used
    )

    if save_to_history:
        db_save_menu(record)

    return jsonify({"ok": True, **record})


@menu_analyzer_bp.route("/api/menus/history", methods=["GET"])
def get_history():
    """Lista menus salvos com paginação e busca opcional."""
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    q = request.args.get("q", "")
    return jsonify(db_get_all(page, per_page, q))


@menu_analyzer_bp.route("/api/menus/compare", methods=["GET"])
def compare_menus():
    """Compara dois menus salvos lado a lado."""
    a_id = request.args.get("a", "")
    b_id = request.args.get("b", "")
    if not a_id or not b_id:
        return jsonify({"ok": False, "error": "Parâmetros 'a' e 'b' são obrigatórios"}), 400

    menu_a = db_get_one(a_id)
    menu_b = db_get_one(b_id)
    if not menu_a:
        return jsonify({"ok": False, "error": f"Menu '{a_id}' não encontrado"}), 404
    if not menu_b:
        return jsonify({"ok": False, "error": f"Menu '{b_id}' não encontrado"}), 404

    # Calcula diff
    def safe_float(v):
        return float(v) if v is not None else 0.0

    sum_a = menu_a.get("summary", {})
    sum_b = menu_b.get("summary", {})
    diff = {
        "price_avg_diff": round(safe_float(sum_a.get("price_avg")) - safe_float(sum_b.get("price_avg")), 2),
        "items_diff": sum_a.get("total_items", 0) - sum_b.get("total_items", 0),
        "vegan_diff": sum_a.get("dietary_counts", {}).get("vegan", 0) - sum_b.get("dietary_counts", {}).get("vegan", 0),
        "vegetarian_diff": sum_a.get("dietary_counts", {}).get("vegetarian", 0) - sum_b.get("dietary_counts", {}).get("vegetarian", 0),
    }

    return jsonify({"ok": True, "a": menu_a, "b": menu_b, "diff": diff})


@menu_analyzer_bp.route("/api/menus/<menu_id>", methods=["GET"])
def get_menu_detail(menu_id):
    """Retorna detalhe completo de um menu."""
    menu = db_get_one(menu_id)
    if not menu:
        return jsonify({"ok": False, "error": "Menu não encontrado"}), 404
    return jsonify({"ok": True, **menu})


@menu_analyzer_bp.route("/api/menus/<menu_id>", methods=["DELETE"])
def delete_menu_route(menu_id):
    """Remove um menu do histórico."""
    if db_delete_menu(menu_id):
        # Remover export se existir
        export_path = get_export_path(menu_id)
        if os.path.exists(export_path):
            os.remove(export_path)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Menu não encontrado"}), 404


@menu_analyzer_bp.route("/api/menus/<menu_id>/export", methods=["POST"])
def export_menu(menu_id):
    """Gera e retorna URL para o HTML exportável do menu."""
    menu = db_get_one(menu_id)
    if not menu:
        return jsonify({"ok": False, "error": "Menu não encontrado"}), 404

    html_content = generate_export_html(menu)
    export_path = get_export_path(menu_id)
    with open(export_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    restaurant = menu.get("restaurant_name", "Cardapio").replace(" ", "_")
    date = menu.get("analyzed_at", "")[:10]
    download_name = f"{restaurant}_{date}.html"

    return jsonify({
        "ok": True,
        "url": f"/api/menus/export/{menu_id}.html",
        "filename": download_name,
    })


@menu_analyzer_bp.route("/api/menus/export/<filename>", methods=["GET"])
def serve_export(filename):
    """Serve arquivo HTML exportado. Path traversal sanitizado."""
    safe_name = os.path.basename(filename)
    if not safe_name.endswith(".html"):
        return jsonify({"ok": False, "error": "Arquivo não encontrado"}), 404

    file_path = os.path.join(EXPORTS_DIR, safe_name)
    if not os.path.exists(file_path):
        return jsonify({"ok": False, "error": "Export não encontrado. Gere novamente."}), 404

    return send_file(file_path, mimetype="text/html")
