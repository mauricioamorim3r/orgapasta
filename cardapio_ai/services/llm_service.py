"""LLM providers and prompt orchestration."""

import json
import os

from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'))

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

SYSTEM_PROMPT = """Voce e um especialista em analise de cardapios de restaurantes.

Quando receber fotos, faca uma analise estruturada em cinco frentes:
1. Extrair com precisao nomes, descricoes e precos.
2. Organizar os pratos em categorias.
3. Estimar calorias, alergenos, ingredientes principais, tamanho de porcao e nivel de picancia.
4. Calcular inteligencia de preco com minimo, maximo, media, moeda detectada e faixa geral.
5. Gerar destaques, avisos de leitura, pistas de culinaria e sugestoes de combos.

Responda somente com JSON valido seguindo exatamente este schema:

{
  "categories": [
    {
      "name": "nome da categoria",
      "items": [
        {
          "id": "uuid-gerado",
          "name": "nome do prato",
          "description": "descricao",
          "price": 22.9,
          "price_raw": "R$ 22,90",
          "calories_estimate": 350,
                    "ingredients_main": ["tomate", "queijo"],
                    "portion_size": "individual",
                    "spice_level": "none",
          "allergens": ["gluten"],
          "tags": ["vegetarian"],
          "badges": ["best_value"],
                    "value_score": 8.5,
                    "confidence": 0.92
        }
      ]
    }
  ],
  "summary": {
    "total_items": 24,
        "detected_currency": "BRL",
        "languages_detected": ["pt-BR"],
        "cuisine_hints": ["brasileira", "italiana"],
        "warnings": ["Alguns precos nao estavam totalmente legiveis"],
    "price_min": 18.0,
    "price_max": 89.0,
    "price_avg": 42.5,
    "price_range": "$$",
    "price_range_label": "Moderado ($$)",
    "highlights": {
      "best_value": {"item_id": "uuid", "item_name": "nome"},
      "chefs_choice": {"item_id": "uuid", "item_name": "nome"},
      "healthy_pick": {"item_id": "uuid", "item_name": "nome"},
      "popular_combo": [
        {"item_id": "uuid", "item_name": "nome"},
        {"item_id": "uuid", "item_name": "nome"}
      ]
    },
    "allergen_counts": {
      "gluten": 12,
      "lactose": 8,
      "nuts": 3,
      "shellfish": 2,
      "eggs": 5,
      "soy": 1
    },
    "dietary_counts": {
      "vegan": 4,
            "vegetarian": 9,
            "gluten_free": 3
        },
        "combo_suggestions": [
            {
                "title": "Almoco leve",
                "items": ["Salada da casa", "Limonada"],
                "total_price": 32.0,
                "reason": "Boa combinacao de frescor e preco acessivel"
            }
        ]
  },
  "raw_analysis": "Resumo narrativo do cardapio."
}
"""


def _normalize_analysis(analysis: dict) -> dict:
        categories = analysis.get('categories') if isinstance(analysis.get('categories'), list) else []
        normalized_categories = []
        for category in categories:
                items = category.get('items') if isinstance(category.get('items'), list) else []
                normalized_items = []
                for item in items:
                        normalized_items.append({
                                'id': item.get('id', ''),
                                'name': item.get('name', ''),
                                'description': item.get('description', ''),
                                'price': item.get('price'),
                                'price_raw': item.get('price_raw', ''),
                                'calories_estimate': item.get('calories_estimate'),
                                'ingredients_main': item.get('ingredients_main', []),
                                'portion_size': item.get('portion_size', ''),
                                'spice_level': item.get('spice_level', 'unknown'),
                                'allergens': item.get('allergens', []),
                                'tags': item.get('tags', []),
                                'badges': item.get('badges', []),
                                'value_score': item.get('value_score'),
                                'confidence': item.get('confidence'),
                        })
                normalized_categories.append({
                        'name': category.get('name', 'Sem categoria'),
                        'items': normalized_items,
                })

        summary = analysis.get('summary') if isinstance(analysis.get('summary'), dict) else {}
        normalized_summary = {
                'total_items': summary.get('total_items', sum(len(category['items']) for category in normalized_categories)),
                'detected_currency': summary.get('detected_currency', 'BRL'),
                'languages_detected': summary.get('languages_detected', []),
                'cuisine_hints': summary.get('cuisine_hints', []),
                'warnings': summary.get('warnings', []),
                'price_min': summary.get('price_min'),
                'price_max': summary.get('price_max'),
                'price_avg': summary.get('price_avg'),
                'price_range': summary.get('price_range', ''),
                'price_range_label': summary.get('price_range_label', ''),
                'highlights': summary.get('highlights', {}),
                'allergen_counts': summary.get('allergen_counts', {}),
                'dietary_counts': {
                        'vegan': summary.get('dietary_counts', {}).get('vegan', 0),
                        'vegetarian': summary.get('dietary_counts', {}).get('vegetarian', 0),
                        'gluten_free': summary.get('dietary_counts', {}).get('gluten_free', 0),
                },
                'combo_suggestions': summary.get('combo_suggestions', []),
        }

        return {
                'categories': normalized_categories,
                'summary': normalized_summary,
                'raw_analysis': analysis.get('raw_analysis', ''),
        }


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:])
        if '```' in text:
            text = text[: text.rfind('```')]
    return text.strip()


def _user_prompt(photo_count: int, restaurant_name: str) -> str:
    return (
        f'Analise o cardapio mostrado nas {photo_count} foto(s).\n'
        f'Nome do restaurante: {restaurant_name or "Desconhecido"}.\n'
        'Retorne a analise completa em JSON, sem nenhum texto fora do JSON.'
    )


def call_claude_vision(images: list[tuple[str, str]], restaurant_name: str) -> dict:
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == 'sua_chave_anthropic_aqui':
        raise RuntimeError('ANTHROPIC_API_KEY nao configurada no arquivo .env.')

    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    content = []
    for image_base64, mime_type in images:
        content.append({
            'type': 'image',
            'source': {
                'type': 'base64',
                'media_type': mime_type,
                'data': image_base64,
            },
        })
    content.append({'type': 'text', 'text': _user_prompt(len(images), restaurant_name)})

    response = client.messages.create(
        model='claude-sonnet-4-5',
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': content}],
    )
    return json.loads(_strip_fences(response.content[0].text))


def call_openai_vision(images: list[tuple[str, str]], restaurant_name: str) -> dict:
    if not OPENAI_API_KEY or OPENAI_API_KEY == 'sua_chave_openai_aqui':
        raise RuntimeError('OPENAI_API_KEY nao configurada no arquivo .env.')

    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    content = []
    for image_base64, mime_type in images:
        content.append({
            'type': 'image_url',
            'image_url': {
                'url': f'data:{mime_type};base64,{image_base64}',
                'detail': 'high',
            },
        })
    content.append({'type': 'text', 'text': _user_prompt(len(images), restaurant_name)})

    response = client.chat.completions.create(
        model='gpt-4o',
        max_tokens=4096,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': content},
        ],
    )
    return json.loads(_strip_fences(response.choices[0].message.content or ''))


def call_gemini_vision(images: list[tuple[str, str]], restaurant_name: str) -> dict:
    if not GEMINI_API_KEY or GEMINI_API_KEY == 'sua_chave_gemini_aqui':
        raise RuntimeError('GEMINI_API_KEY nao configurada no arquivo .env.')

    import urllib.error as urllib_error
    import urllib.request as urllib_request

    parts = []
    for image_base64, mime_type in images:
        parts.append({'inline_data': {'mime_type': mime_type, 'data': image_base64}})
    parts.append({'text': SYSTEM_PROMPT + '\n\n' + _user_prompt(len(images), restaurant_name)})

    payload = json.dumps({
        'contents': [{'parts': parts}],
        'generationConfig': {'maxOutputTokens': 4096},
    }).encode('utf-8')

    url = (
        'https://generativelanguage.googleapis.com/v1beta/models/'
        f'gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'
    )
    request = urllib_request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    try:
        with urllib_request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read())
    except urllib_error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Gemini API erro {exc.code}: {body[:200]}') from exc

    raw_text = result['candidates'][0]['content']['parts'][0]['text']
    return json.loads(_strip_fences(raw_text))


def call_groq_vision(images: list[tuple[str, str]], restaurant_name: str) -> dict:
    if not GROQ_API_KEY or GROQ_API_KEY == 'sua_chave_groq_aqui':
        raise RuntimeError('GROQ_API_KEY nao configurada no arquivo .env.')

    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY)
    content = []
    for image_base64, mime_type in images:
        content.append({
            'type': 'image_url',
            'image_url': {'url': f'data:{mime_type};base64,{image_base64}'},
        })
    content.append({'type': 'text', 'text': SYSTEM_PROMPT + '\n\n' + _user_prompt(len(images), restaurant_name)})

    response = client.chat.completions.create(
        model='meta-llama/llama-4-scout-17b-16e-instruct',
        messages=[{'role': 'user', 'content': content}],
        max_tokens=4096,
    )
    return json.loads(_strip_fences(response.choices[0].message.content or ''))


PROVIDERS: dict[str, tuple[str, object]] = {
    'claude': ('Claude Sonnet 4.5', call_claude_vision),
    'openai': ('GPT-4o', call_openai_vision),
    'gemini': ('Gemini 2.0 Flash', call_gemini_vision),
    'groq': ('Llama 4 Scout', call_groq_vision),
}


def call_llm_vision(images: list[tuple[str, str]], restaurant_name: str, provider: str) -> tuple[dict, str]:
    selected_provider = provider if provider in PROVIDERS else 'claude'
    model_label, handler = PROVIDERS[selected_provider]
    return _normalize_analysis(handler(images, restaurant_name)), model_label