# NavMed v2 — Features Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar 8 novas funcionalidades ao NavMed em 3 fases (acesso rápido, inteligência, organização) sem quebrar nenhum comportamento existente.

**Architecture:** Evolução incremental sobre o Flask app existente em `navmed/`. Fase 1 é puramente frontend (JS/CSS) + 1 endpoint novo. Fase 2 adiciona dois módulos Python novos (`monitor.py`, `stats.py`) registrados no app principal. Fase 3 estende o modelo de dados no `config.json` e adiciona UI de tags e estatísticas.

**Tech Stack:** Python 3 + Flask, tkinter (widget), Vanilla JS, CSS custom properties, JSON (config), `os`/`shutil`/`threading` (stdlib)

**Spec:** `docs/superpowers/specs/2026-03-27-navmed-features-design.md`

---

## Chunk 1: Fase 1 — Acesso Rápido

### Arquivos afetados

| Ação | Arquivo | Responsabilidade |
|------|---------|-----------------|
| Modify | `navmed/static/app.js` | Botão copiar, tipo arquivo, busca live |
| Modify | `navmed/static/style.css` | Estilos: botão copiar, input busca, item tipo file |
| Modify | `navmed/templates/index.html` | Input de busca no header da sidebar |
| Modify | `navmed/api/folders.py` | Endpoint `GET /api/search?q=` |
| Modify | `navmed/api/config_api.py` | `DEFAULT_CONFIG` sem mudança — `type:"file"` já é suportado |
| Modify | `navmed/templates/index.html` | Modal: radio "Arquivo" + label dinâmico |

---

### Task 1: Botão "Copiar caminho"

**Files:**
- Modify: `navmed/static/style.css`
- Modify: `navmed/static/app.js`
- Modify: `navmed/templates/index.html`

- [ ] **Step 1: Adicionar botão Copiar no HTML do painel de detalhe**

Em `navmed/templates/index.html`, dentro de `<div class="detail-header-actions">`, adicionar após o botão `btn-detail-open`:

```html
<button id="btn-detail-copy" class="copy-btn" style="display:none"
        title="Copiar caminho para a área de transferência">⎘ Copiar</button>
```

- [ ] **Step 2: Adicionar CSS para o botão copiar**

Em `navmed/static/style.css`, após o estilo de `.open-btn`:

```css
.copy-btn {
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
  transition: border-color .15s, color .15s, background .15s;
}
.copy-btn:hover { border-color: var(--accent); color: var(--accent); }
.copy-btn.copied {
  border-color: var(--success);
  color: var(--success);
  background: rgba(34,197,94,.08);
}
```

- [ ] **Step 3: Implementar lógica de copiar em app.js**

Em `navmed/static/app.js`, localizar a função que popula o painel de detalhe (onde `btn-detail-open` é configurado). Adicionar logo após a lógica do botão Abrir:

```js
// Botão Copiar
const copyBtn = document.getElementById('btn-detail-copy');
if (item.path) {
  copyBtn.style.display = '';
  copyBtn.onclick = async () => {
    try {
      await navigator.clipboard.writeText(item.path);
      copyBtn.textContent = '✔ Copiado!';
      copyBtn.classList.add('copied');
      setTimeout(() => {
        copyBtn.textContent = '⎘ Copiar';
        copyBtn.classList.remove('copied');
      }, 2000);
    } catch {
      // Fallback para ambientes sem clipboard API
      const ta = document.createElement('textarea');
      ta.value = item.path;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      copyBtn.textContent = '✔ Copiado!';
      setTimeout(() => { copyBtn.textContent = '⎘ Copiar'; }, 2000);
    }
  };
} else {
  copyBtn.style.display = 'none';
}
```

- [ ] **Step 4: Verificar manualmente no browser**

1. Iniciar app: `cd navmed && python app.py`
2. Abrir `http://localhost:5200`
3. Selecionar qualquer item com path
4. Confirmar que botão "⎘ Copiar" aparece ao lado de "Abrir"
5. Clicar — confirmar que o path vai para o clipboard (colar no Notepad para verificar)
6. Confirmar feedback visual "✔ Copiado!" por 2s

- [ ] **Step 5: Commit**

```bash
git add navmed/static/app.js navmed/static/style.css navmed/templates/index.html
git commit -m "feat(navmed): add copy-path button to detail panel"
```

---

### Task 2: Tipo de item "Arquivo"

**Files:**
- Modify: `navmed/templates/index.html`
- Modify: `navmed/static/app.js`
- Modify: `navmed/static/style.css`

- [ ] **Step 1: Adicionar radio "Arquivo" no modal**

Em `navmed/templates/index.html`, no `<div class="radio-group">` do modal, adicionar após o radio `url`:

```html
<label class="radio-label">
  <input type="radio" name="f-type" value="file" id="r-file"> Arquivo
</label>
```

- [ ] **Step 2: Atualizar label dinâmico do campo path**

Em `navmed/static/app.js`, localizar o event listener que ouve mudanças nos radios `f-type` (troca o label de "Caminho" para "URL"). Estender para cobrir o valor `"file"`:

```js
// Dentro do handler de mudança de tipo:
const labels = { group: null, folder: 'Caminho da pasta', url: 'URL', file: 'Caminho do arquivo' };
const placeholders = {
  group: '',
  folder: 'C:\\caminho\\da\\pasta ou \\\\servidor\\share',
  url: 'https://...',
  file: 'C:\\caminho\\do\\arquivo.xlsx'
};
document.getElementById('lbl-path').textContent = labels[type] || 'Caminho';
document.getElementById('f-path').placeholder = placeholders[type] || '';
document.getElementById('fg-path').style.display = type === 'group' ? 'none' : '';
```

- [ ] **Step 3: Ícone automático por extensão**

Em `navmed/static/app.js`, adicionar função helper antes do código do modal:

```js
function iconForFile(path) {
  if (!path) return '📄';
  const ext = path.split('.').pop().toLowerCase();
  const map = {
    xlsx: '📊', xls: '📊', csv: '📊',
    pdf: '📕',
    docx: '📝', doc: '📝',
    pptx: '📊', ppt: '📊',
    txt: '📋', log: '📋',
    zip: '🗜️', rar: '🗜️',
    png: '🖼️', jpg: '🖼️', jpeg: '🖼️',
  };
  return map[ext] || '📄';
}
```

Chamar `iconForFile(path)` para pré-preencher o campo `f-icon` quando o tipo for `"file"` e o path for alterado:

```js
// No handler de input do campo f-path, quando tipo === 'file':
if (currentType === 'file' && !iconManuallyChanged) {
  document.getElementById('f-icon').value = iconForFile(e.target.value);
}
```

- [ ] **Step 4: CSS para distinguir itens tipo file na árvore**

Em `navmed/static/style.css`:

```css
.tree-item[data-type="file"] .tree-label {
  font-style: italic;
}
.tree-item[data-type="file"]::after {
  content: attr(data-ext);
  font-size: 9px;
  color: var(--muted);
  margin-left: 4px;
  text-transform: uppercase;
  opacity: .7;
}
```

- [ ] **Step 5: Garantir que `os.startfile()` funciona para arquivos**

Em `navmed/api/folders.py`, a lógica de `/api/open` já usa `os.startfile(path)` para paths que não são HTTP. Verificar que arquivos sem barra final funcionam — não há mudança necessária, apenas confirmar.

Testar manualmente:
1. Criar item tipo "Arquivo" apontando para um `.xlsx` existente
2. Clicar "Abrir" — Excel deve abrir o arquivo
3. Confirmar ícone automático aparece no campo

- [ ] **Step 6: Commit**

```bash
git add navmed/templates/index.html navmed/static/app.js navmed/static/style.css
git commit -m "feat(navmed): add file item type with auto-icon by extension"
```

---

### Task 3: Busca cruzada na sidebar

**Files:**
- Modify: `navmed/templates/index.html`
- Modify: `navmed/static/app.js`
- Modify: `navmed/static/style.css`
- Modify: `navmed/api/folders.py`

- [ ] **Step 1: Adicionar input de busca no HTML da sidebar**

Em `navmed/templates/index.html`, dentro de `<div id="sidebar">`, após `<div id="sidebar-header">` e antes de `<div id="tree-container">`:

```html
<div id="search-bar">
  <input id="search-input" type="text" placeholder="🔍  Buscar em tudo…"
         autocomplete="off" spellcheck="false">
  <button id="search-clear" style="display:none" aria-label="Limpar busca">✕</button>
</div>
```

- [ ] **Step 2: CSS para a barra de busca**

Em `navmed/static/style.css`:

```css
#search-bar {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 4px;
  position: relative;
}
#search-input {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 28px 5px 10px;
  color: var(--text);
  font-size: 12px;
  outline: none;
  transition: border-color .15s;
}
#search-input:focus { border-color: var(--accent); }
#search-input::placeholder { color: var(--muted); }
#search-clear {
  position: absolute;
  right: 18px;
  background: none;
  border: none;
  color: var(--muted);
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
}
#search-clear:hover { color: var(--text); }

/* Itens ocultos durante filtro */
.tree-item.search-hidden { display: none; }
.tree-item.search-match .tree-label { color: var(--accent); }
```

- [ ] **Step 3: Implementar filtro live em app.js**

Em `navmed/static/app.js`, adicionar após o código de renderização da árvore:

```js
// ── Busca cruzada ──────────────────────────────────────────────────────────
let searchDebounce = null;

function normalizeSearch(str) {
  return (str || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function itemMatchesQuery(item, q) {
  if (!q) return true;
  const fields = [item.label, item.path, item.notes, ...(item.tags || [])];
  return fields.some(f => normalizeSearch(f).includes(q));
}

function applySearch(q) {
  const norm = normalizeSearch(q);
  const items = document.querySelectorAll('.tree-item');
  items.forEach(el => {
    el.classList.remove('search-hidden', 'search-match');
  });
  if (!norm) return;

  items.forEach(el => {
    const id = el.dataset.id;
    const item = findItemById(id, window._navConfig?.tree || []);
    if (!item) return;
    if (itemMatchesQuery(item, norm)) {
      el.classList.add('search-match');
      // Mostrar ancestrais
      let parent = el.parentElement?.closest('.tree-item');
      while (parent) {
        parent.classList.remove('search-hidden');
        parent = parent.parentElement?.closest('.tree-item');
      }
    } else {
      el.classList.add('search-hidden');
    }
  });
}

document.getElementById('search-input')?.addEventListener('input', e => {
  clearTimeout(searchDebounce);
  const q = e.target.value.trim();
  document.getElementById('search-clear').style.display = q ? '' : 'none';
  searchDebounce = setTimeout(() => applySearch(q), 200);
});

document.getElementById('search-clear')?.addEventListener('click', () => {
  document.getElementById('search-input').value = '';
  document.getElementById('search-clear').style.display = 'none';
  applySearch('');
});
```

**Nota:** Antes de implementar, rodar `grep -n "findItemById\|_navConfig\|navConfig" navmed/static/app.js` para confirmar os nomes exatos das referências globais de estado da árvore e adaptar o código se necessário.

- [ ] **Step 4: Endpoint /api/search no backend**

Em `navmed/api/folders.py`, adicionar endpoint ao final do arquivo:

```python
# ── GET /api/search ────────────────────────────────────────────────────────────
@folders_bp.route("/api/search", methods=["GET"])
def search_items():
    """
    Query param: ?q=termo
    Busca recursivamente em todos os itens do config (label, path, notes, tags).
    Retorna lista de itens que batem, com breadcrumb de ancestrais.
    """
    from api.config_api import load_config

    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify({"ok": True, "results": []})

    config = load_config()
    results = []

    def _normalize(s):
        import unicodedata
        return unicodedata.normalize("NFD", (s or "").lower())

    def _matches(item):
        fields = [item.get("label", ""), item.get("path", ""),
                  item.get("notes", "")] + item.get("tags", [])
        return any(_normalize(q) in _normalize(f) for f in fields)

    def _walk(nodes, breadcrumb):
        for node in nodes:
            crumb = breadcrumb + [node.get("label", "")]
            if _matches(node):
                results.append({
                    "id": node.get("id"),
                    "label": node.get("label"),
                    "type": node.get("type"),
                    "path": node.get("path", ""),
                    "icon": node.get("icon", "📁"),
                    "breadcrumb": crumb[:-1],
                })
            _walk(node.get("children", []), crumb)

    _walk(config.get("tree", []), [])
    return jsonify({"ok": True, "results": results})
```

- [ ] **Step 5: Verificar manualmente**

1. Adicionar alguns itens com labels e paths variados
2. Digitar parte do nome na barra de busca
3. Confirmar que apenas itens que batem aparecem
4. Confirmar que ao limpar (✕) a árvore volta ao normal
5. Testar `GET http://localhost:5200/api/search?q=pasta` no browser

- [ ] **Step 6: Commit**

```bash
git add navmed/templates/index.html navmed/static/app.js navmed/static/style.css navmed/api/folders.py
git commit -m "feat(navmed): cross-search bar with live filter and /api/search endpoint"
```

---

## Chunk 2: Fase 2 — Inteligência

### Arquivos afetados

| Ação | Arquivo | Responsabilidade |
|------|---------|-----------------|
| Create | `navmed/api/monitor.py` | Thread de monitoramento de pastas, detecção de arquivos novos |
| Create | `navmed/api/version_detect.py` | Regex para detecção de versão em nome de arquivo |
| Modify | `navmed/api/folders.py` | Integrar detecção de versão no scan; endpoint `/api/monitor/toggle` |
| Modify | `navmed/app.py` | Registrar blueprint monitor; iniciar thread ao subir |
| Modify | `navmed/static/app.js` | Toggle sentinela no painel; badge de alertas |
| Modify | `navmed/static/style.css` | Toggle switch, badge alerta, highlight de última versão |
| Modify | `navmed/templates/index.html` | Área de alerta no topo; toggle no painel de detalhe |
| Modify | `navmed/templates/creator.html` | Campo "arquivo modelo" por nó na árvore |
| Modify | `navmed/api/folders.py` | Suporte a templates no `/api/mkdir` |

---

### Task 4: Módulo monitor de pastas (Sentinela)

**Files:**
- Create: `navmed/api/monitor.py`
- Modify: `navmed/app.py`
- Modify: `navmed/api/folders.py`
- Modify: `navmed/static/app.js`
- Modify: `navmed/static/style.css`
- Modify: `navmed/templates/index.html`

- [ ] **Step 1: Criar `navmed/api/monitor.py`**

```python
"""
NavMed — Monitor de Pastas (Sentinela)
========================================
Thread background que verifica periodicamente pastas marcadas como
monitoradas e grava alertas em config["pending_alerts"] quando novos
arquivos são detectados.

Uso:
    from api.monitor import start_monitor
    start_monitor()   # chamado uma vez no startup do app
"""

import os
import threading
import time
from datetime import datetime

from api.config_api import load_config, modify_config

_monitor_thread = None
_stop_event = threading.Event()


def _scan_filenames(path: str) -> set:
    """Retorna conjunto de nomes de arquivo no nível raiz da pasta."""
    try:
        return {e.name for e in os.scandir(path) if e.is_file()}
    except (PermissionError, FileNotFoundError, OSError):
        return set()


def _run_monitor():
    """Loop principal da thread de monitoramento."""
    while not _stop_event.is_set():
        try:
            config = load_config()
            tree = config.get("tree", [])
            monitored = []

            def _collect(nodes):
                for node in nodes:
                    if node.get("monitor") and node.get("path") and node.get("type") == "folder":
                        monitored.append(node)
                    _collect(node.get("children", []))

            _collect(tree)

            for item in monitored:
                path = item["path"]
                item_id = item["id"]
                interval = item.get("monitor_interval_min", 5)
                last_check_key = f"_last_check_{item_id}"

                # Verificar se já passou o intervalo desde o último check
                now = time.time()
                last_check = config.get("_monitor_timestamps", {}).get(item_id, 0)
                if now - last_check < interval * 60:
                    continue

                current_files = _scan_filenames(path)
                baseline = set(item.get("last_seen_files", []))
                new_files = current_files - baseline

                if new_files:
                    def _update(cfg, _id=item_id, _new=new_files, _all=current_files, _path=path, _label=item.get("label", path)):
                        # Atualizar baseline
                        for node in _walk_flat(cfg.get("tree", [])):
                            if node.get("id") == _id:
                                node["last_seen_files"] = list(_all)
                                break
                        # Gravar alerta
                        alerts = cfg.setdefault("pending_alerts", [])
                        alerts.append({
                            "id": _id,
                            "label": _label,
                            "path": _path,
                            "new_files": sorted(_new),
                            "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        })
                        # Limitar a 20 alertas
                        cfg["pending_alerts"] = alerts[-20:]
                        # Atualizar timestamp
                        cfg.setdefault("_monitor_timestamps", {})[_id] = time.time()

                    modify_config(_update)
                else:
                    def _update_ts(cfg, _id=item_id):
                        cfg.setdefault("_monitor_timestamps", {})[_id] = time.time()
                    modify_config(_update_ts)

        except Exception:
            pass  # Monitor nunca deve derrubar o app

        _stop_event.wait(timeout=30)  # Ciclo a cada 30s; intervalo real por item


def _walk_flat(nodes):
    """Iterador plano sobre todos os nós da árvore."""
    for node in nodes:
        yield node
        yield from _walk_flat(node.get("children", []))


def start_monitor():
    """Iniciar thread de monitoramento (idempotente)."""
    global _monitor_thread
    if _monitor_thread and _monitor_thread.is_alive():
        return
    _stop_event.clear()
    _monitor_thread = threading.Thread(target=_run_monitor, daemon=True, name="navmed-monitor")
    _monitor_thread.start()


def stop_monitor():
    """Parar thread de monitoramento."""
    _stop_event.set()
```

- [ ] **Step 2: Registrar monitor no app.py**

Em `navmed/app.py`, adicionar import e chamada de start no bloco de inicialização:

```python
from api.monitor import start_monitor

# Após registrar blueprints, antes do app.run():
start_monitor()
```

- [ ] **Step 3: Endpoint `/api/monitor/toggle` em folders.py**

Em `navmed/api/folders.py`, adicionar ao final:

```python
@folders_bp.route("/api/monitor/toggle", methods=["POST"])
def monitor_toggle():
    """
    Body: {"id": "...", "enabled": true, "interval_min": 5}
    Liga/desliga monitoramento de uma pasta e define baseline de arquivos.
    """
    from api.monitor import _scan_filenames

    body = request.get_json(force=True) or {}
    item_id = body.get("id", "")
    enabled = bool(body.get("enabled", False))
    interval = int(body.get("interval_min", 5))

    if not item_id:
        return jsonify({"ok": False, "error": "id is required"}), 400

    # Helper definido ANTES de _update para evitar NameError no closure
    def _walk_flat_cfg(nodes):
        for n in nodes:
            yield n
            yield from _walk_flat_cfg(n.get("children", []))

    def _update(cfg):
        for node in _walk_flat_cfg(cfg.get("tree", [])):
            if node.get("id") == item_id:
                node["monitor"] = enabled
                node["monitor_interval_min"] = interval
                if enabled and node.get("path"):
                    node["last_seen_files"] = list(_scan_filenames(node["path"]))
                break

    modify_config(_update)
    return jsonify({"ok": True})


@folders_bp.route("/api/monitor/alerts", methods=["GET"])
def monitor_alerts():
    """Retorna alertas pendentes e limpa a lista."""
    from api.config_api import load_config

    def _clear(cfg):
        alerts = cfg.get("pending_alerts", [])
        cfg["pending_alerts"] = []
        return alerts

    config = load_config()
    alerts = config.get("pending_alerts", [])
    if alerts:
        def _clear_alerts(cfg):
            cfg["pending_alerts"] = []
        modify_config(_clear_alerts)
    return jsonify({"ok": True, "alerts": alerts})
```

- [ ] **Step 4: Toggle e badge no frontend (app.js)**

Em `navmed/static/app.js`, na seção que renderiza o painel de detalhe de pastas, adicionar após os metadados:

```js
// Toggle sentinela
if (item.type === 'folder') {
  const monitorHtml = `
    <div id="monitor-row" class="monitor-row">
      <label class="toggle-wrap">
        <input type="checkbox" id="monitor-toggle" ${item.monitor ? 'checked' : ''}>
        <span class="toggle-track"><span class="toggle-thumb"></span></span>
      </label>
      <span class="monitor-label">
        Monitorar novos arquivos
        ${item.monitor ? '<span class="monitor-active">● ativo</span>' : ''}
      </span>
      <select id="monitor-interval" class="monitor-select" ${!item.monitor ? 'disabled' : ''}>
        <option value="5" ${item.monitor_interval_min==5?'selected':''}>5 min</option>
        <option value="10" ${item.monitor_interval_min==10?'selected':''}>10 min</option>
        <option value="30" ${item.monitor_interval_min==30?'selected':''}>30 min</option>
      </select>
    </div>`;
  document.getElementById('detail-sections').insertAdjacentHTML('beforeend', monitorHtml);

  document.getElementById('monitor-toggle').addEventListener('change', async e => {
    const enabled = e.target.checked;
    const interval = parseInt(document.getElementById('monitor-interval').value);
    await fetch('/api/monitor/toggle', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({id: item.id, enabled, interval_min: interval})
    });
    // Recarregar item para refletir estado
    window._navConfig = await (await fetch('/api/config')).json();
  });
}
```

Adicionar poll de alertas (verificar a cada 60s):

```js
// Poll de alertas da sentinela
async function checkAlerts() {
  try {
    const r = await fetch('/api/monitor/alerts');
    const d = await r.json();
    if (d.alerts && d.alerts.length > 0) {
      showAlertBadge(d.alerts);
    }
  } catch { /* silencioso */ }
}
setInterval(checkAlerts, 60000);
checkAlerts(); // Verificar imediatamente ao carregar

function showAlertBadge(alerts) {
  let badge = document.getElementById('alert-badge');
  if (!badge) {
    badge = document.createElement('div');
    badge.id = 'alert-badge';
    badge.className = 'alert-badge';
    document.getElementById('sidebar-header').appendChild(badge);
  }
  badge.textContent = `🔔 ${alerts.length} novo${alerts.length > 1 ? 's' : ''}`;
  badge.onclick = () => {
    alert(alerts.map(a => `📁 ${a.label}\nArquivos novos: ${a.new_files.join(', ')}`).join('\n\n'));
    badge.remove();
  };
}
```

- [ ] **Step 5: CSS para toggle e badge**

Em `navmed/static/style.css`:

```css
/* Toggle sentinela */
.monitor-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(34,197,94,.05);
  border: 1px solid rgba(34,197,94,.15);
  border-radius: 8px;
  margin-top: 10px;
}
.toggle-wrap { display: flex; align-items: center; cursor: pointer; }
.toggle-track {
  width: 32px; height: 18px;
  background: var(--border);
  border-radius: 9px;
  position: relative;
  transition: background .2s;
}
input[type="checkbox"]:checked ~ .toggle-track { background: var(--success); }
.toggle-thumb {
  width: 14px; height: 14px;
  background: #fff;
  border-radius: 50%;
  position: absolute;
  top: 2px; left: 2px;
  transition: left .2s;
}
input[type="checkbox"]:checked ~ .toggle-track .toggle-thumb { left: 16px; }
input[type="checkbox"] { display: none; }
.monitor-label { font-size: 11px; color: var(--muted); flex: 1; }
.monitor-active { color: var(--success); margin-left: 6px; }
.monitor-select {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--muted);
  font-size: 10px;
  padding: 2px 4px;
}

/* Badge de alerta */
.alert-badge {
  background: var(--danger);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
  cursor: pointer;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%,100% { opacity: 1; }
  50% { opacity: .7; }
}
```

- [ ] **Step 6: Verificar manualmente**

1. Ligar monitoramento numa pasta de teste
2. Adicionar um arquivo nessa pasta manualmente
3. Aguardar até 30s (ciclo do monitor) ou chamar `GET /api/monitor/alerts` diretamente
4. Confirmar badge aparece na sidebar com nome do arquivo novo
5. Confirmar que desligar o toggle remove o monitoramento

- [ ] **Step 7: Badge no widget flutuante (navmed_widget.pyw)**

Em `navmed/navmed_widget.pyw`, na função de refresh (chamada pelo polling de 5s), adicionar verificação de `pending_alerts` no `config.json`:

```python
# Dentro da função _refresh() ou equivalente no widget:
alerts = config.get("pending_alerts", [])
if alerts:
    # Mostrar badge vermelho com contagem
    if hasattr(self, '_alert_label'):
        self._alert_label.config(
            text=f"🔔 {len(alerts)}",
            fg="#ef4444",
            cursor="hand2"
        )
        self._alert_label.bind("<Button-1>", lambda e, a=alerts: self._show_alerts(a))

def _show_alerts(self, alerts):
    import tkinter.messagebox as mb
    msg = "\n\n".join(
        f"📁 {a['label']}\nNovos: {', '.join(a['new_files'])}"
        for a in alerts
    )
    mb.showinfo("NavMed — Novos arquivos", msg)
```

Adicionar `_alert_label` no `__init__` do widget caso não exista:

```python
self._alert_label = tk.Label(self._frame, text="", bg=BG, font=("Segoe UI", 9))
self._alert_label.pack(anchor="w", padx=8)
```

- [ ] **Step 8: Commit**

```bash
git add navmed/api/monitor.py navmed/api/folders.py navmed/app.py \
        navmed/static/app.js navmed/static/style.css navmed/templates/index.html \
        navmed/navmed_widget.pyw
git commit -m "feat(navmed): add folder sentinel (monitor thread + toggle UI + alert badge + widget badge)"
```

---

### Task 5: Detecção de última versão

**Files:**
- Create: `navmed/api/version_detect.py`
- Modify: `navmed/api/folders.py`
- Modify: `navmed/static/app.js`
- Modify: `navmed/static/style.css`

- [ ] **Step 1: Criar `navmed/api/version_detect.py`**

```python
"""
NavMed — Detecção de Versão em Nomes de Arquivo
================================================
Detecta padrões de versionamento em listas de nomes de arquivo e
retorna o arquivo mais recente de cada série.

Padrões suportados:
  _v1, _v2, _v10        (sufixo _vN)
  _V1, _V2              (maiúsculo)
  Rev1, Rev2, Rev10     (prefixo Rev)
  _r1, _r2              (sufixo _rN)
  -v1, -v2              (hífen)
  (1), (2), (10)        (parênteses)
"""

import re
from collections import defaultdict

# Regex para capturar série + número de versão
_VERSION_RE = re.compile(
    r'^(.*?)(?:_v|_V|-v|-V|Rev|rev|_r|-r|\()(\d+)(?:\))?(\.[^.]+)?$'
)


def detect_latest_versions(filenames: list[str]) -> dict[str, str]:
    """
    Recebe lista de nomes de arquivo, retorna dict {nome_arquivo: "latest"}
    para o arquivo de maior versão de cada série.

    Exemplo:
        detect_latest_versions(["rel_v1.xlsx", "rel_v2.xlsx", "outro.pdf"])
        → {"rel_v2.xlsx": "latest"}
    """
    series: dict[str, list[tuple[int, str]]] = defaultdict(list)

    for name in filenames:
        m = _VERSION_RE.match(name)
        if m:
            base, num, ext = m.group(1), int(m.group(2)), m.group(3) or ""
            series_key = base.rstrip("_- ") + ext
            series[series_key].append((num, name))

    result = {}
    for key, versions in series.items():
        if len(versions) > 1:  # Só destacar se há mais de uma versão
            _, latest_name = max(versions, key=lambda x: x[0])
            result[latest_name] = "latest"

    return result
```

- [ ] **Step 2: Integrar no scan em folders.py**

Em `navmed/api/folders.py`, adicionar import no topo:

```python
from api.version_detect import detect_latest_versions
```

Na função `scan_path()`, antes do `return jsonify(...)`, adicionar:

```python
# Detecção de versão nos arquivos recentes
all_names = [name for _, name, _ in all_files]
version_flags = detect_latest_versions(all_names)

# Adicionar flag "latest_version" nos recent_files
for rf in recent_files:
    rf["latest_version"] = rf["name"] in version_flags
```

Adicionar `"version_flags": version_flags` na resposta JSON.

- [ ] **Step 3: Destacar última versão no frontend**

Em `navmed/static/app.js`, na função que renderiza a lista de arquivos recentes no painel de detalhe, adicionar badge condicional:

```js
// Dentro do template de cada arquivo recente:
const latestBadge = file.latest_version
  ? '<span class="version-badge">Última versão</span>'
  : '';
// Adicionar latestBadge ao HTML do item de arquivo
```

- [ ] **Step 4: CSS do badge de versão**

Em `navmed/static/style.css`:

```css
.version-badge {
  display: inline-block;
  background: rgba(59,130,246,.15);
  border: 1px solid rgba(59,130,246,.4);
  color: #93c5fd;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .04em;
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: 6px;
  vertical-align: middle;
}
```

- [ ] **Step 5: Verificar manualmente**

1. Criar arquivos de teste: `relatorio_v1.xlsx`, `relatorio_v2.xlsx`, `relatorio_v3.xlsx`
2. Registrar a pasta no NavMed e abrir seu painel de detalhe
3. Confirmar que `relatorio_v3.xlsx` aparece com badge "Última versão"
4. Confirmar que arquivos sem versão não recebem badge

- [ ] **Step 6: Commit**

```bash
git add navmed/api/version_detect.py navmed/api/folders.py \
        navmed/static/app.js navmed/static/style.css
git commit -m "feat(navmed): auto-detect latest file version in folder scan"
```

---

### Task 6: Templates de arquivo no criador de estrutura

**Files:**
- Modify: `navmed/templates/creator.html`
- Modify: `navmed/api/folders.py`

- [ ] **Step 1: Campo de template no nó do criador**

Em `navmed/templates/creator.html`, localizar o template HTML de cada nó da árvore (o elemento `<li>` ou similar que representa uma pasta no criador). Adicionar campo de template após o input de nome:

```html
<div class="node-template-row">
  <input type="text" class="node-template-input"
         placeholder="Arquivo modelo (opcional): C:\templates\modelo.xlsx"
         title="Caminho de um arquivo que será copiado para esta pasta ao criar">
</div>
```

- [ ] **Step 2: Incluir templates no payload enviado ao backend**

Em `navmed/templates/creator.html`, verificar primeiro se existe um arquivo separado `navmed/static/creator.js` com `grep -rn "buildNode\|api/mkdir" navmed/`. Se existir, editar esse arquivo; caso contrário, editar o bloco `<script>` interno do `creator.html`. Na função que monta o objeto `tree` para enviar ao `/api/mkdir`, incluir o valor do campo template em cada nó:

```js
function buildNode(el) {
  return {
    name: el.querySelector('.node-name-input').value.trim(),
    template: el.querySelector('.node-template-input')?.value.trim() || '',
    children: Array.from(el.querySelectorAll(':scope > .node-children > .node-item'))
                   .map(buildNode)
  };
}
```

- [ ] **Step 3: Processar templates no backend `/api/mkdir`**

Em `navmed/api/folders.py`, na função `_create_tree()` dentro de `make_dirs()`, adicionar cópia do arquivo template após `os.makedirs()`:

```python
import shutil

# Após os.makedirs(full_path, exist_ok=True):
template = node.get("template", "").strip()
if template and os.path.isfile(template):
    try:
        dest = os.path.join(full_path, os.path.basename(template))
        shutil.copy2(template, dest)
        results.append({"path": dest, "created": True, "template": True, "error": None})
    except (PermissionError, OSError) as te:
        results.append({"path": template, "created": False, "template": True, "error": str(te)})
```

- [ ] **Step 4: Verificar manualmente**

1. Abrir o criador de estrutura
2. Criar dois nós de pasta; colocar path de um arquivo `.xlsx` existente no campo template do primeiro
3. Aprovar e criar
4. Verificar no File Explorer que a pasta foi criada e o arquivo modelo está dentro
5. Verificar que a pasta sem template também foi criada normalmente

- [ ] **Step 5: Commit**

```bash
git add navmed/templates/creator.html navmed/api/folders.py
git commit -m "feat(navmed): support file templates in folder structure creator"
```

---

## Chunk 3: Fase 3 — Organização

### Arquivos afetados

| Ação | Arquivo | Responsabilidade |
|------|---------|-----------------|
| Create | `navmed/api/stats.py` | Leitura de access_log, cálculo de métricas, endpoint `/api/stats` |
| Modify | `navmed/api/config_api.py` | `DEFAULT_CONFIG` com `all_tags` e `stats.access_log`; endpoint PATCH tags |
| Modify | `navmed/api/folders.py` | Gravar em `access_log` no `/api/open` |
| Modify | `navmed/static/app.js` | UI de tags no modal; filtro de tags na sidebar; aba Stats |
| Modify | `navmed/static/style.css` | Chips de tag, filtro de tags, aba Stats, gráfico de barras |
| Modify | `navmed/templates/index.html` | Chips de tags no painel detalhe; aba Stats no rodapé |

---

### Task 7: Tags & Projetos

**Files:**
- Modify: `navmed/api/config_api.py`
- Modify: `navmed/static/app.js`
- Modify: `navmed/static/style.css`
- Modify: `navmed/templates/index.html`

- [ ] **Step 1: Atualizar DEFAULT_CONFIG com all_tags**

Em `navmed/api/config_api.py`, adicionar ao `DEFAULT_CONFIG`:

```python
DEFAULT_CONFIG = {
    "version": 1,
    "tree": [],
    "recent": [],
    "favorites": [],
    "all_tags": [],
    "widget": {"x": 100, "y": 100, "width": 220, "height": 400},
}
```

- [ ] **Step 2: Endpoint PATCH /api/config/tags**

Em `navmed/api/config_api.py`, adicionar endpoint:

```python
@config_bp.route("/api/config/tags", methods=["PATCH"])
def patch_item_tags():
    """
    Body: {"id": "item-uuid", "tags": ["tag1", "tag2"]}
    Atualiza tags de um item e sincroniza all_tags global.
    """
    body = request.get_json(force=True) or {}
    item_id = body.get("id", "")
    tags = body.get("tags", [])

    if not item_id:
        return jsonify({"ok": False, "error": "id is required"}), 400

    if not isinstance(tags, list):
        return jsonify({"ok": False, "error": "tags must be an array"}), 400

    # Sanitizar tags: lowercase, sem espaços duplos
    tags = [t.strip().lower() for t in tags if t.strip()]

    def _update(cfg):
        def _walk(nodes):
            for node in nodes:
                if node.get("id") == item_id:
                    node["tags"] = tags
                    return True
                if _walk(node.get("children", [])):
                    return True
            return False

        _walk(cfg.get("tree", []))

        # Reconstruir índice global de tags
        all_tags = set()
        def _collect_tags(nodes):
            for node in nodes:
                all_tags.update(node.get("tags", []))
                _collect_tags(node.get("children", []))
        _collect_tags(cfg.get("tree", []))
        cfg["all_tags"] = sorted(all_tags)

    modify_config(_update)
    return jsonify({"ok": True})
```

- [ ] **Step 3: UI de tags no painel de detalhe**

Em `navmed/templates/index.html`, no painel de detalhe (`#item-detail`), após o bloco de header, adicionar zona de tags:

```html
<div id="detail-tags" class="detail-tags-row" style="display:none">
  <div id="tag-chips"></div>
  <input id="tag-input" type="text" placeholder="+ adicionar tag"
         class="tag-input" autocomplete="off">
</div>
```

- [ ] **Step 4: Lógica de tags em app.js**

Em `navmed/static/app.js`, na função que popula o painel de detalhe:

```js
// Renderizar chips de tags
const tagsRow = document.getElementById('detail-tags');
const tagChips = document.getElementById('tag-chips');
const tagInput = document.getElementById('tag-input');

tagsRow.style.display = '';
tagChips.innerHTML = (item.tags || []).map(t =>
  `<span class="tag-chip" data-tag="${t}">${t}<button class="tag-remove" onclick="removeTag('${item.id}','${t}')">×</button></span>`
).join('');

// Autocomplete de all_tags
const allTags = window._navConfig?.all_tags || [];
tagInput.setAttribute('list', 'tag-datalist');
let dl = document.getElementById('tag-datalist');
if (!dl) { dl = document.createElement('datalist'); dl.id = 'tag-datalist'; document.body.appendChild(dl); }
dl.innerHTML = allTags.map(t => `<option value="${t}">`).join('');

tagInput.onkeydown = async e => {
  if (e.key === 'Enter' && tagInput.value.trim()) {
    const newTag = tagInput.value.trim().toLowerCase();
    const currentTags = [...(item.tags || [])];
    if (!currentTags.includes(newTag)) {
      currentTags.push(newTag);
      await fetch('/api/config/tags', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: item.id, tags: currentTags})
      });
      window._navConfig = await (await fetch('/api/config')).json();
      // Re-renderizar painel
      selectItem(item.id);
    }
    tagInput.value = '';
  }
};

window.removeTag = async (id, tag) => {
  const updItem = findItemById(id, window._navConfig?.tree || []);
  const newTags = (updItem?.tags || []).filter(t => t !== tag);
  await fetch('/api/config/tags', {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id, tags: newTags})
  });
  window._navConfig = await (await fetch('/api/config')).json();
  selectItem(id);
};
```

- [ ] **Step 5: Filtro de tags na sidebar**

Em `navmed/templates/index.html`, entre a barra de busca e `#tree-container`:

```html
<div id="tag-filter-bar" style="display:none">
  <div id="tag-filter-chips"></div>
</div>
```

Em `navmed/static/app.js`, função para renderizar e aplicar filtro:

```js
function renderTagFilterBar(allTags) {
  const bar = document.getElementById('tag-filter-bar');
  const chips = document.getElementById('tag-filter-chips');
  if (!allTags || allTags.length === 0) { bar.style.display = 'none'; return; }
  bar.style.display = '';
  chips.innerHTML = allTags.map(t =>
    `<span class="tag-filter-chip" data-tag="${t}" onclick="toggleTagFilter('${t}')">${t}</span>`
  ).join('');
}

let activeTagFilters = new Set();
window.toggleTagFilter = (tag) => {
  activeTagFilters.has(tag) ? activeTagFilters.delete(tag) : activeTagFilters.add(tag);
  document.querySelectorAll('.tag-filter-chip').forEach(el => {
    el.classList.toggle('active', activeTagFilters.has(el.dataset.tag));
  });
  applyTagFilter();
};

function applyTagFilter() {
  if (activeTagFilters.size === 0) {
    document.querySelectorAll('.tree-item').forEach(el => el.classList.remove('tag-hidden'));
    return;
  }
  document.querySelectorAll('.tree-item').forEach(el => {
    const id = el.dataset.id;
    const item = findItemById(id, window._navConfig?.tree || []);
    const itemTags = item?.tags || [];
    const match = [...activeTagFilters].some(t => itemTags.includes(t));
    el.classList.toggle('tag-hidden', !match);
  });
}
```

- [ ] **Step 6: CSS de tags**

Em `navmed/static/style.css`:

```css
/* Tags no painel de detalhe */
.detail-tags-row { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; padding: 4px 0 10px; }
.tag-chip {
  display: inline-flex; align-items: center; gap: 4px;
  background: rgba(59,130,246,.12); border: 1px solid rgba(59,130,246,.35);
  color: #93c5fd; font-size: 11px; border-radius: 4px; padding: 2px 8px;
}
.tag-remove { background: none; border: none; color: inherit; cursor: pointer; font-size: 12px; padding: 0 0 0 2px; opacity: .7; }
.tag-remove:hover { opacity: 1; }
.tag-input {
  background: transparent; border: none; border-bottom: 1px dashed var(--border);
  color: var(--muted); font-size: 11px; padding: 2px 6px; outline: none; width: 120px;
}
.tag-input:focus { border-bottom-color: var(--accent); color: var(--text); }

/* Filtro de tags na sidebar */
#tag-filter-bar { padding: 6px 10px; border-bottom: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 4px; }
.tag-filter-chip {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 4px; padding: 2px 8px; font-size: 10px; color: var(--muted); cursor: pointer;
  transition: all .15s;
}
.tag-filter-chip:hover { border-color: var(--accent); color: var(--accent); }
.tag-filter-chip.active { background: rgba(59,130,246,.15); border-color: var(--accent); color: var(--accent); }
.tree-item.tag-hidden { display: none; }
```

- [ ] **Step 7: Verificar manualmente**

1. Adicionar tags a 3 itens diferentes (ex: "obra", "cliente-a", "norma")
2. Confirmar chips aparecem no painel de detalhe de cada item
3. Confirmar que o filtro de tags aparece na sidebar com as tags criadas
4. Clicar numa tag no filtro — apenas itens com aquela tag aparecem
5. Clicar novamente — filtro desativa e todos os itens voltam

- [ ] **Step 8: Commit**

```bash
git add navmed/api/config_api.py navmed/static/app.js navmed/static/style.css navmed/templates/index.html
git commit -m "feat(navmed): add tags system with sidebar filter and per-item chips"
```

---

### Task 8: Painel de Estatísticas de Uso

**Files:**
- Create: `navmed/api/stats.py`
- Modify: `navmed/api/folders.py`
- Modify: `navmed/templates/index.html`
- Modify: `navmed/static/app.js`
- Modify: `navmed/static/style.css`

- [ ] **Step 1: Criar `navmed/api/stats.py`**

```python
"""
NavMed — Estatísticas de Uso
==============================
Calcula métricas de acesso a partir do access_log gravado no config.json.

Endpoint:
  GET /api/stats  → top_items, recent_accesses, weekly_chart
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, jsonify

from api.config_api import load_config

stats_bp = Blueprint("stats_bp", __name__)


@stats_bp.route("/api/stats", methods=["GET"])
def get_stats():
    """
    Retorna:
      top_items: top 5 itens mais acessados (id, label, icon, count)
      recent_accesses: últimos 10 acessos (label, ts formatado)
      weekly_chart: contagem de acessos por dia nos últimos 7 dias (lista de 7 ints)
    """
    config = load_config()
    log = config.get("stats", {}).get("access_log", [])

    if not log:
        return jsonify({
            "ok": True,
            "top_items": [],
            "recent_accesses": [],
            "weekly_chart": [0] * 7,
        })

    # Top 5 mais acessados
    counter = Counter(entry["id"] for entry in log)
    tree_flat = list(_walk_flat(config.get("tree", [])))
    item_map = {n["id"]: n for n in tree_flat}

    top_items = []
    for item_id, count in counter.most_common(5):
        node = item_map.get(item_id)
        if node:
            top_items.append({
                "id": item_id,
                "label": node.get("label", "?"),
                "icon": node.get("icon", "📁"),
                "count": count,
            })

    # Últimos 10 acessos
    recent = []
    for entry in reversed(log[-10:]):
        try:
            dt = datetime.fromisoformat(entry["ts"])
            ts_fmt = dt.strftime("%d/%m %H:%M")
        except (KeyError, ValueError):
            ts_fmt = entry.get("ts", "")
        recent.append({"label": entry.get("label", "?"), "ts": ts_fmt})
    recent.reverse()

    # Gráfico semanal (últimos 7 dias)
    today = datetime.now().date()
    day_counts = defaultdict(int)
    for entry in log:
        try:
            dt = datetime.fromisoformat(entry["ts"]).date()
            delta = (today - dt).days
            if 0 <= delta < 7:
                day_counts[delta] += 1
        except (KeyError, ValueError):
            pass
    weekly_chart = [day_counts[i] for i in range(6, -1, -1)]  # [6 dias atrás … hoje]

    return jsonify({
        "ok": True,
        "top_items": top_items,
        "recent_accesses": recent,
        "weekly_chart": weekly_chart,
    })


def _walk_flat(nodes):
    for node in nodes:
        yield node
        yield from _walk_flat(node.get("children", []))
```

- [ ] **Step 2: Registrar stats_bp no app.py**

Em `navmed/app.py`:

```python
from api.stats import stats_bp
app.register_blueprint(stats_bp)
```

- [ ] **Step 3: Gravar access_log no /api/open**

Em `navmed/api/folders.py`, verificar se `from datetime import datetime` já está importado no topo do arquivo (já existe na implementação atual). Se não estiver, adicionar antes das funções. Então, na função `open_path()`, dentro do bloco `if item_id:`, substituir o bloco `_update_recent` existente por:

```python
def _update_log(cfg):
    recent = cfg.get("recent", [])
    recent = [r for r in recent if r != item_id]
    recent.insert(0, item_id)
    cfg["recent"] = recent[:10]
    # Gravar no access_log
    label = body.get("label", "")
    log = cfg.setdefault("stats", {}).setdefault("access_log", [])
    log.append({
        "id": item_id,
        "label": label,
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    })
    # Manter máx 500 entradas
    cfg["stats"]["access_log"] = log[-500:]

modify_config(_update_log)
```

**Nota:** O endpoint `/api/open` já recebe `id` no body. Precisará também receber `label` — atualizar chamada JS no frontend para incluir `label: item.label` no payload.

- [ ] **Step 4: Aba Stats no HTML da sidebar**

Em `navmed/templates/index.html`, substituir `<div id="sidebar-footer">` para incluir abas:

```html
<div id="sidebar-tabs">
  <button class="sidebar-tab active" data-tab="tree" onclick="switchTab('tree')">🗂 Itens</button>
  <button class="sidebar-tab" data-tab="stats" onclick="switchTab('stats')">📊 Stats</button>
</div>
<div id="tab-stats" style="display:none;padding:12px;overflow-y:auto;flex:1">
  <div id="stats-content">
    <p class="subtitle" style="text-align:center;margin-top:20px">Carregando...</p>
  </div>
</div>
```

- [ ] **Step 5: Lógica de renderização de Stats em app.js**

Em `navmed/static/app.js`:

```js
window.switchTab = (tab) => {
  document.querySelectorAll('.sidebar-tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.getElementById('tree-container').style.display = tab === 'tree' ? '' : 'none';
  document.getElementById('tab-stats').style.display = tab === 'stats' ? '' : 'none';
  if (tab === 'stats') loadStats();
};

async function loadStats() {
  const el = document.getElementById('stats-content');
  try {
    const r = await fetch('/api/stats');
    const d = await r.json();
    if (!d.ok) { el.innerHTML = '<p class="subtitle">Sem dados ainda.</p>'; return; }

    // Gráfico SVG inline (barras)
    const max = Math.max(...d.weekly_chart, 1);
    const bars = d.weekly_chart.map((v, i) => {
      const h = Math.round((v / max) * 40);
      const days = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'];
      const today = new Date().getDay();
      const dayLabel = days[(today - 6 + i + 7) % 7];
      return `<g>
        <rect x="${i*28+4}" y="${44-h}" width="20" height="${h}" fill="var(--accent)" rx="3" opacity=".8"/>
        <text x="${i*28+14}" y="56" text-anchor="middle" font-size="8" fill="var(--muted)">${dayLabel}</text>
        ${v > 0 ? `<text x="${i*28+14}" y="${44-h-3}" text-anchor="middle" font-size="8" fill="var(--muted)">${v}</text>` : ''}
      </g>`;
    }).join('');
    const svg = `<svg width="200" height="60" style="display:block;margin:0 auto 12px">${bars}</svg>`;

    // Top itens
    const topHtml = d.top_items.length === 0 ? '<p class="subtitle">Nenhum acesso registrado.</p>' :
      '<div class="stats-top">' +
      d.top_items.map((it, i) =>
        `<div class="stats-top-item">
          <span class="stats-rank">${i+1}</span>
          <span class="stats-icon">${it.icon}</span>
          <span class="stats-label">${it.label}</span>
          <span class="stats-count">${it.count}×</span>
        </div>`
      ).join('') + '</div>';

    // Recentes
    const recentHtml = '<div class="stats-recent">' +
      d.recent_accesses.map(a =>
        `<div class="stats-recent-item"><span>${a.label}</span><span class="stats-ts">${a.ts}</span></div>`
      ).join('') + '</div>';

    el.innerHTML = `
      <p class="label" style="margin-bottom:6px">Acessos (7 dias)</p>
      ${svg}
      <p class="label" style="margin-bottom:6px">Mais acessados</p>
      ${topHtml}
      <p class="label" style="margin:10px 0 6px">Últimos acessos</p>
      ${recentHtml}
    `;
  } catch { el.innerHTML = '<p class="subtitle">Erro ao carregar.</p>'; }
}
```

- [ ] **Step 6: CSS da aba Stats**

Em `navmed/static/style.css`:

```css
/* Abas da sidebar */
#sidebar-tabs {
  display: flex;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
.sidebar-tab {
  flex: 1; padding: 7px 0; background: transparent; border: none;
  color: var(--muted); font-size: 11px; cursor: pointer; transition: color .15s, background .15s;
  border-top: 2px solid transparent;
}
.sidebar-tab:hover { color: var(--text); background: var(--bg-hover); }
.sidebar-tab.active { color: var(--accent); border-top-color: var(--accent); }

/* Stats */
.stats-top { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
.stats-top-item { display: flex; align-items: center; gap: 6px; font-size: 11px; }
.stats-rank { width: 14px; color: var(--muted); font-size: 10px; text-align: right; }
.stats-icon { font-size: 14px; }
.stats-label { flex: 1; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stats-count { color: var(--accent); font-weight: 700; font-size: 11px; }
.stats-recent { display: flex; flex-direction: column; gap: 3px; }
.stats-recent-item { display: flex; justify-content: space-between; font-size: 10px; color: var(--muted); }
.stats-recent-item span:first-child { color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 130px; }
.stats-ts { flex-shrink: 0; margin-left: 6px; }
```

- [ ] **Step 7: Verificar manualmente**

1. Abrir e clicar em 5+ itens diferentes várias vezes
2. Clicar na aba "📊 Stats" na sidebar
3. Confirmar: gráfico de barras dos 7 dias, top 5 itens, lista dos últimos 10 acessos
4. Verificar que os dados são consistentes com o que foi acessado
5. Testar `GET http://localhost:5200/api/stats` diretamente

- [ ] **Step 8: Commit**

```bash
git add navmed/api/stats.py navmed/app.py navmed/api/folders.py \
        navmed/templates/index.html navmed/static/app.js navmed/static/style.css
git commit -m "feat(navmed): add usage stats panel with weekly chart and top items"
```

---

## Finalização

- [ ] **Push para GitHub**

```bash
git push origin master
```

- [ ] **Atualizar ZIP**

```bash
python -c "
import zipfile, os
base = r'C:\Users\mauri\Downloads\xquads'
exclude = {'.git','.claude','.superpowers','__pycache__','venv'}
with zipfile.ZipFile(r'C:\Users\mauri\Downloads\orgapasta.zip','w',zipfile.ZIP_DEFLATED) as z:
    for root,dirs,files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in exclude]
        for f in files:
            if not f.endswith(('.pyc','.pyo')):
                fp = os.path.join(root,f)
                z.write(fp, os.path.join('orgapasta', os.path.relpath(fp, base)))
print('ZIP atualizado')
"
```
