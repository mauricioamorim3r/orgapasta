# NavMed — Design de Funcionalidades v2
**Data:** 2026-03-27
**Status:** Aprovado

## Contexto

O NavMed é um gerenciador de links de pastas/URLs de rede com widget flutuante, construído em Flask + Python + HTML. O usuário acumula dezenas de locais frequentemente acessados em diferentes partes da rede, e o objetivo é eliminar o tempo perdido navegando por diretórios para encontrar o que já conhece.

Este documento especifica 8 novas funcionalidades organizadas em 3 fases de implementação, todas evolutivas sobre o app existente — sem quebrar nenhuma feature atual.

---

## Abordagem Escolhida

**Opção C — Quick wins primeiro, depois inteligência:**

- **Fase 1 (Acesso rápido):** Clipboard + Link para arquivo + Busca cruzada
- **Fase 2 (Inteligência):** Sentinela de mudanças + Última versão automática + Templates de arquivo
- **Fase 3 (Organização):** Tags & Projetos + Painel de uso

---

## Arquitetura — Camadas afetadas

| Camada | Mudanças |
|---|---|
| `config.json` | Novos campos: `tags`, `monitor`, `monitor_interval_min`, `last_seen_files`, `all_tags`, `stats.access_log` |
| `api/folders.py` | Novo endpoint `/api/search`; detecção de versão no scan |
| `api/config_api.py` | Suporte a escrita de tags e flag de monitoramento |
| `static/app.js` | Busca live na sidebar, filtro por tag, botão copiar path, toggle sentinela |
| `static/style.css` | Chips de tag, barra de busca, aba Stats |
| `navmed_widget.pyw` | Badge de notificação quando sentinela detecta mudança |
| **Novo** `api/monitor.py` | Thread background que observa pastas monitoradas |
| **Novo** `api/stats.py` | Leitura do histórico de acessos e geração de métricas |

---

## Modelo de Dados

### Item (config.json → tree[])

```json
{
  "id": "uuid",
  "type": "folder | url | group | file",
  "label": "string",
  "path": "string",
  "icon": "emoji",
  "notes": "string",
  "tags": ["string"],
  "monitor": false,
  "monitor_interval_min": 5,
  "last_seen_files": ["filename"]
}
```

### Raiz do config.json

```json
{
  "tree": [],
  "recent": [],
  "favorites": [],
  "all_tags": ["string"],
  "stats": {
    "access_log": [
      {"id": "uuid", "ts": "ISO8601", "label": "string"}
    ]
  }
}
```

---

## Fase 1 — Acesso Rápido

### 📋 Copiar caminho
- **Onde:** Painel de detalhe de cada item, ao lado do botão "Abrir"
- **Como:** Botão `⎘ Copiar` → `navigator.clipboard.writeText(path)` → feedback visual "Copiado!" por 2s
- **Escopo:** Funciona para todos os tipos (folder, url, file, group com path)

### 📄 Tipo Arquivo
- **Onde:** Modal de criação/edição — novo radio button "Arquivo"
- **Como:** Usuário seleciona um arquivo (path digitado ou colado). `os.startfile()` abre diretamente no app padrão do SO
- **Ícone padrão:** Detectado por extensão (📊 xlsx, 📄 pdf, 📝 docx, 📋 csv, genérico 📄)
- **Distinção visual na árvore:** Itens do tipo `file` mostram ícone menor com extensão

### 🔍 Busca cruzada
- **Onde:** Barra de busca no topo da sidebar (abaixo do header)
- **Como:** Filtra em tempo real (debounce 200ms) por label, path, notas e tags em todos os nós da árvore
- **Resultado:** Árvore colapsa, mostra só itens que batem + seus ancestrais (contexto)
- **Reset:** Limpar campo restaura árvore completa
- **Endpoint:** `/api/search?q=termo` como alternativa (para uso do widget)

---

## Fase 2 — Inteligência

### 🔔 Sentinela de mudanças
- **Onde:** Toggle "Monitorar" no painel de detalhe de pastas (não disponível para URLs)
- **Como:** `api/monitor.py` inicia thread ao ligar o app; verifica `os.scandir()` a cada N min; compara com `last_seen_files`; se detectar arquivo novo, grava notificação em `config["pending_alerts"]`
- **Notificação:** Toast no HTML + badge vermelho no widget flutuante
- **Configurável:** Intervalo por pasta (5, 10, 30 min)

### 🏷️ Última versão automática
- **Onde:** Seção "Arquivos recentes" no painel de scan da pasta
- **Como:** Regex detecta padrões `_v\d+`, `_V\d+`, `Rev\d+`, `_r\d+` no nome do arquivo; agrupa por série; destaca o de número mais alto com badge "Última versão"
- **Sem configuração:** Automático sempre que a pasta é scaneada

### 📐 Templates de arquivo
- **Onde:** Criador de estrutura de pastas — cada nó pode ter templates associados
- **Como:** Campo "Arquivos modelo" por nó; ao criar a estrutura, `shutil.copy()` copia cada template para dentro da pasta criada
- **Armazenamento:** Templates referenciados por path absoluto (devem existir no momento da criação)

---

## Fase 3 — Organização

### 🏷️ Tags & Projetos
- **Onde:** Modal de edição de item + barra de filtro na sidebar
- **Como:** Campo de tags (input com autocomplete de `all_tags`); chips clicáveis na sidebar filtram a árvore mostrando só itens com aquela tag
- **Multi-tag:** Filtro com múltiplas tags usa lógica OR (mostra item que tenha qualquer uma)
- **`all_tags`:** Índice global atualizado automaticamente quando tag é adicionada/removida

### 📊 Painel de uso
- **Onde:** Aba "Stats" no rodapé da sidebar (ao lado da aba "Itens")
- **Como:** `api/stats.py` lê `access_log` (gravado em cada `/api/open`) e retorna top 5 mais acessados, últimos 10 acessos com data/hora, contagem semanal por dia
- **Visual:** Lista ranqueada + mini gráfico de barras em SVG inline
- **Sem dependências externas:** Tudo em Python puro + SVG

---

## Comportamento por Feature

| Feature | Onde aparece | Implementação |
|---|---|---|
| 📋 Copiar caminho | Painel detalhe | `navigator.clipboard.writeText()` |
| 📄 Tipo Arquivo | Modal novo item | `os.startfile()` direto no arquivo |
| 🔍 Busca cruzada | Topo sidebar | Filtro JS em tempo real + `/api/search` |
| 🔔 Sentinela | Painel detalhe | Thread Python background com `os.scandir()` |
| 🏷️ Última versão | Painel scan | Regex de detecção de versão no scan |
| 📐 Templates | Criador estrutura | `shutil.copy()` na criação de pastas |
| 🏷️ Tags | Modal + sidebar | Chips + filtro OR na árvore |
| 📊 Stats | Aba sidebar | Lê `access_log` + SVG inline |

---

## Critérios de Sucesso

- Fase 1: Usuário copia path sem abrir o File Explorer; acha qualquer item em <3s digitando
- Fase 2: Recebe notificação de arquivo novo sem precisar checar a pasta manualmente
- Fase 3: Filtra itens por projeto/cliente com 1 clique; vê quais pastas usa mais

## Estimativa de Implementação

| Fase | Features | Tempo estimado |
|---|---|---|
| Fase 1 | Clipboard, Arquivo, Busca | ~2h |
| Fase 2 | Sentinela, Última versão, Templates | ~3h |
| Fase 3 | Tags, Stats | ~2h |
| **Total** | **8 features** | **~7h** |
