# orgapasta

Este repositorio agora contem dois aplicativos Python independentes.

## Apps

### FotoCardapio AI

Aplicativo standalone para analisar fotos de cardapios com LLMs, salvar o historico localmente e exportar resultados em HTML.

- Pasta: `cardapio_ai/`
- Porta padrao: `5300`
- Start rapido: `cardapio_ai\start_cardapio_ai.bat`
- Documentacao detalhada: `cardapio_ai/README.md`

### NavMed

Aplicativo legado de gerenciamento de pastas e links com widget desktop.

- Pasta: `navmed/`
- Porta padrao: `5200`
- Start rapido: `navmed\navmed.bat`

## Estrutura resumida

```text
orgapasta/
  cardapio_ai/   -> produto de analise de cardapios por foto
  navmed/        -> gerenciador de pastas e links
```

## Como executar

### Executar FotoCardapio AI

1. Entre em `cardapio_ai/`.
2. Instale dependencias com `python -m pip install -r requirements.txt`.
3. Copie `.env.example` para `.env`.
4. Preencha pelo menos uma chave de API.
5. Execute `start_cardapio_ai.bat` ou `python app.py`.

### Executar NavMed

1. Entre em `navmed/`.
2. Instale dependencias com `python -m pip install -r requirements.txt`.
3. Execute `navmed.bat` ou `python app.py`.

## Dados gerados em runtime

Os artefatos locais do FotoCardapio AI nao devem ir para o git.

- `cardapio_ai/.env`
- `cardapio_ai/data/menus_db.json`
- `cardapio_ai/exports/`
- `cardapio_ai/uploads/`

O mesmo vale para os artefatos antigos do `navmed`.
