# FotoCardapio AI

Projeto standalone para analisar fotos de cardapios com LLMs.

## O que esta pronto

- Upload de ate 5 fotos por analise
- Persistencia fisica das fotos por analise em pastas proprias
- Analise com Claude, GPT-4o, Gemini ou Groq
- Historico local em JSON
- Comparacao entre cardapios salvos
- Exportacao de um cardapio em HTML
- Schema ampliado com ingredientes, porcao, picancia, moeda, idiomas, culinaria e combos sugeridos
- Estrutura separada da NavMed

## Estrutura

```text
cardapio_ai/
  app.py
  requirements.txt
  .env.example
  start_cardapio_ai.bat
  api/
    __init__.py
    routes.py
  services/
    __init__.py
    export_service.py
    image_utils.py
    llm_service.py
    menu_repository.py
  data/
    menus_db.json
  exports/
  uploads/
    <menu_id>/
      photo_01.jpg
  static/
    app.js
    style.css
  templates/
    index.html
```

## Como iniciar

1. Entre na pasta `cardapio_ai`.
2. Instale as dependencias com `python -m pip install -r requirements.txt`.
3. Copie `.env.example` para `.env`.
4. Preencha pelo menos uma chave de API.
5. Rode `python app.py`.
6. Abra `http://localhost:5300`.

## Onde ficam os dados

- Historico local: `data/menus_db.json`
- Exports HTML: `exports/`
- Uploads por analise: `uploads/<menu_id>/`

## Observacao

O projeto nao depende da estrutura de pastas, widget ou configuracao da NavMed. Voce pode trabalhar apenas com esta pasta.

## Campos extras da analise

- `ingredients_main`
- `portion_size`
- `spice_level`
- `confidence`
- `detected_currency`
- `languages_detected`
- `cuisine_hints`
- `warnings`
- `combo_suggestions`
