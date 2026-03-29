/**
 * NavMed — Gerenciador de Pastas e Links
 * Vanilla JS, sem dependências externas.
 */

// ── State ───────────────────────────────────────────────────────────────────
let config = { tree: [], recent: [], widget: {} };
let selectedId = null;

// Set of group IDs that are currently collapsed
const collapsedGroups = new Set();

// Drag-and-drop state
let draggedId = null;
let draggedParentRef = null; // array containing the dragged item

// Modal state
let modalMode = 'create'; // 'create' | 'edit'
let modalParentId = null;  // parent id when creating a child
let modalEditId = null;    // item id when editing

// ── Bootstrap ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  fetchConfig();

  document.getElementById('btn-add-root').addEventListener('click', () => {
    openModal('create', null, null);
  });

  // Modal controls
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('btn-modal-cancel').addEventListener('click', closeModal);
  document.getElementById('btn-modal-save').addEventListener('click', onModalSave);
  document.getElementById('modal-overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
  });

  // Show/hide path field based on type radio selection
  document.querySelectorAll('input[name="f-type"]').forEach(radio => {
    radio.addEventListener('change', onTypeChange);
  });

  // Detail label autosave on blur
  document.getElementById('detail-label').addEventListener('blur', onDetailLabelBlur);
});

// ── API helpers ─────────────────────────────────────────────────────────────
async function fetchConfig() {
  try {
    const res = await fetch('/api/config');
    config = await res.json();
    renderTree();
  } catch (err) {
    console.error('[NavMed] fetchConfig error:', err);
  }
}

async function saveConfig() {
  try {
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
  } catch (err) {
    console.error('[NavMed] saveConfig error:', err);
  }
}

async function openItem(item) {
  try {
    await fetch('/api/open', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: item.id, path: item.path || item.url || '' }),
    });
  } catch (err) {
    console.error('[NavMed] openItem error:', err);
  }
}

async function scanFolder(path) {
  // Show skeleton while loading
  renderScanSkeleton();

  try {
    const res = await fetch('/api/scan?path=' + encodeURIComponent(path));
    const data = await res.json();

    if (!data.ok) {
      renderScanError(data.error || 'Não foi possível escanear a pasta.');
      return;
    }

    renderScanResults(data);
  } catch (err) {
    renderScanError('Erro ao conectar com o servidor.');
  }
}

// ── Tree rendering ───────────────────────────────────────────────────────────
function renderTree() {
  const container = document.getElementById('tree-container');

  if (!config.tree || config.tree.length === 0) {
    container.innerHTML = '<div class="tree-empty">Nenhum item ainda.<br>Clique em <strong>+ Adicionar grupo raiz</strong> para começar.</div>';
    return;
  }

  const ul = buildTreeUL(config.tree, null);
  container.innerHTML = '';
  container.appendChild(ul);
}

function buildTreeUL(items, parentArray) {
  const ul = document.createElement('ul');
  ul.className = parentArray === null ? 'tree-root' : 'tree-children';

  items.forEach((item, index) => {
    ul.appendChild(buildTreeLI(item, items, index));
  });

  return ul;
}

function buildTreeLI(item, parentArray, index) {
  const li = document.createElement('li');
  li.className = 'tree-item';
  li.dataset.id = item.id;
  if (selectedId === item.id) li.classList.add('selected');

  // Drag and drop
  li.draggable = true;
  li.addEventListener('dragstart', (e) => onDragStart(e, item, parentArray));
  li.addEventListener('dragover', (e) => onDragOver(e, li));
  li.addEventListener('dragleave', () => onDragLeave(li));
  li.addEventListener('drop', (e) => onDrop(e, item, parentArray, index));
  li.addEventListener('dragend', () => onDragEnd(li));

  // Row
  const row = document.createElement('div');
  row.className = 'tree-item-row';

  if (item.type === 'group') {
    // Chevron
    const chevron = document.createElement('span');
    chevron.className = 'tree-chevron' + (collapsedGroups.has(item.id) ? '' : ' open');
    chevron.textContent = '▶';
    row.appendChild(chevron);

    const icon = document.createElement('span');
    icon.className = 'tree-icon';
    icon.textContent = item.icon || '📂';
    row.appendChild(icon);

    const label = document.createElement('span');
    label.className = 'tree-label group-label';
    label.textContent = item.label || 'Grupo';
    row.appendChild(label);

    // Actions
    const actions = buildGroupActions(item, parentArray);
    row.appendChild(actions);

    // Click to toggle collapse
    row.addEventListener('click', (e) => {
      if (e.target.closest('.action-btn')) return;
      toggleGroup(item.id);
    });

  } else {
    // Folder or URL
    const spacer = document.createElement('span');
    spacer.style.width = '12px';
    spacer.style.flexShrink = '0';
    row.appendChild(spacer);

    const icon = document.createElement('span');
    icon.className = 'tree-icon';
    icon.textContent = item.icon || (item.type === 'folder' ? '📁' : '🔗');
    row.appendChild(icon);

    const label = document.createElement('span');
    label.className = 'tree-label';
    label.textContent = item.label || 'Item';
    row.appendChild(label);

    if (item.pinned) {
      const pin = document.createElement('span');
      pin.className = 'tree-pin-indicator';
      pin.textContent = '⭐';
      row.appendChild(pin);
    }

    const actions = buildItemActions(item, parentArray);
    row.appendChild(actions);

    // Click to select + open
    row.addEventListener('click', (e) => {
      if (e.target.closest('.action-btn')) return;
      selectItem(item.id);
      renderDetailPanel(item);
      if (item.type === 'folder') {
        openItem(item);
        scanFolder(item.path || '');
      } else if (item.type === 'url') {
        openItem(item);
      }
    });
  }

  li.appendChild(row);

  // Children (groups and folders can have children)
  if (item.children && item.children.length > 0) {
    const childUL = buildTreeUL(item.children, item.children);
    if (item.type === 'group' && collapsedGroups.has(item.id)) {
      childUL.classList.add('collapsed');
    }
    li.appendChild(childUL);
  }

  return li;
}

function buildGroupActions(item, parentArray) {
  const actions = document.createElement('div');
  actions.className = 'item-actions';

  const addBtn = makeActionBtn('＋', 'add-btn', 'Adicionar filho', () => {
    openModal('create', item.id, null);
  });
  const editBtn = makeActionBtn('✏', 'edit-btn', 'Editar', () => {
    openModal('edit', null, item);
  });
  const delBtn = makeActionBtn('🗑', 'del-btn', 'Excluir', () => {
    deleteItem(item.id);
  });

  actions.append(addBtn, editBtn, delBtn);
  return actions;
}

function buildItemActions(item, parentArray) {
  const actions = document.createElement('div');
  actions.className = 'item-actions';

  const pinBtn = makeActionBtn('⭐', 'pin-btn' + (item.pinned ? ' pinned' : ''), item.pinned ? 'Desafixar' : 'Fixar', () => {
    togglePin(item.id);
  });
  const editBtn = makeActionBtn('✏', 'edit-btn', 'Editar', () => {
    openModal('edit', null, item);
  });
  const delBtn = makeActionBtn('🗑', 'del-btn', 'Excluir', () => {
    deleteItem(item.id);
  });

  actions.append(pinBtn, editBtn, delBtn);
  return actions;
}

function makeActionBtn(icon, classes, title, onClick) {
  const btn = document.createElement('button');
  btn.className = 'action-btn ' + classes;
  btn.title = title;
  btn.textContent = icon;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    onClick();
  });
  return btn;
}

// ── Tree interactions ────────────────────────────────────────────────────────
function toggleGroup(groupId) {
  if (collapsedGroups.has(groupId)) {
    collapsedGroups.delete(groupId);
  } else {
    collapsedGroups.add(groupId);
  }
  renderTree();
}

function selectItem(id) {
  selectedId = id;
  renderTree();
  document.getElementById('welcome-state').style.display = 'none';
  document.getElementById('item-detail').style.display = 'flex';
}

// ── Detail panel ─────────────────────────────────────────────────────────────
function renderDetailPanel(item) {
  const iconEl   = document.getElementById('detail-icon');
  const labelEl  = document.getElementById('detail-label');
  const pathEl   = document.getElementById('detail-path');
  const openBtn  = document.getElementById('btn-detail-open');
  const sections = document.getElementById('detail-sections');

  iconEl.textContent  = item.icon || (item.type === 'folder' ? '📁' : item.type === 'url' ? '🔗' : '📂');
  labelEl.value       = item.label || '';
  labelEl.dataset.id  = item.id;

  if (item.type === 'url') {
    pathEl.textContent = item.path || item.url || '';
    openBtn.style.display = 'inline-block';
    openBtn.onclick = () => openItem(item);
    renderURLSections(item, sections);
  } else if (item.type === 'folder') {
    pathEl.textContent = item.path || '';
    openBtn.style.display = 'inline-block';
    openBtn.onclick = () => openItem(item);
    // scan sections (including notes) are rendered by renderScanSkeleton / renderScanResults
    sections.innerHTML = '';
  } else {
    pathEl.textContent = '';
    openBtn.style.display = 'none';
    sections.innerHTML = '';
    renderNoteSection(item, sections);
  }

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
}

function renderURLSections(item, container) {
  container.innerHTML = '';

  // URL section — built with DOM to avoid inline-handler escaping issues
  const urlSection = makeSummarySection('🔗 Link', '');
  const body = urlSection.querySelector('.summary-section-body');

  const panel = document.createElement('div');
  panel.className = 'url-panel';

  const urlDisplay = document.createElement('div');
  urlDisplay.className = 'url-display';
  urlDisplay.textContent = item.path || item.url || '';

  const openBtn = document.createElement('button');
  openBtn.className = 'open-url-btn';
  openBtn.textContent = 'Abrir URL ↗';
  openBtn.addEventListener('click', () => openItem(item));

  panel.appendChild(urlDisplay);
  panel.appendChild(openBtn);
  body.appendChild(panel);

  container.appendChild(urlSection);

  renderNoteSection(item, container);
}

function renderNoteSection(item, container) {
  const textarea = document.createElement('textarea');
  textarea.className = 'notes-area';
  textarea.placeholder = 'Adicione notas sobre este item...';
  textarea.value = item.notes || '';
  textarea.addEventListener('blur', () => {
    item.notes = textarea.value;
    const found = findItemById(config.tree, item.id);
    if (found) found.item.notes = textarea.value;
    saveConfig();
  });

  const section = makeSummarySection('📝 Notas', '');
  section.querySelector('.summary-section-body').appendChild(textarea);
  container.appendChild(section);
}

function makeSummarySection(title, bodyHTML) {
  const sec = document.createElement('div');
  sec.className = 'summary-section';
  sec.innerHTML = `
    <div class="summary-section-header">
      <span class="summary-section-title">${title}</span>
    </div>
    <div class="summary-section-body">${bodyHTML}</div>
  `;
  return sec;
}

// ── Scan results rendering ───────────────────────────────────────────────────
function renderScanSkeleton() {
  const sections = document.getElementById('detail-sections');
  sections.innerHTML = '';

  const skeletonHTML = `
    <div style="display:flex;flex-direction:column;gap:20px">
      <div class="summary-section">
        <div class="summary-section-header"><span class="summary-section-title">Metadados</span></div>
        <div class="summary-section-body">
          <div class="skeleton-line" style="width:80%"></div>
          <div class="skeleton-line" style="width:60%"></div>
        </div>
      </div>
      <div class="summary-section">
        <div class="summary-section-header"><span class="summary-section-title">Arquivos Recentes</span></div>
        <div class="summary-section-body">
          <div class="skeleton-line"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-line"></div>
        </div>
      </div>
    </div>
  `;

  const wrapper = document.createElement('div');
  wrapper.innerHTML = skeletonHTML;
  sections.appendChild(wrapper.firstElementChild);

  // Re-append notes section after skeleton
  const item = findItemById(config.tree, selectedId);
  if (item) renderNoteSection(item.item, sections);
}

function renderScanError(msg) {
  const sections = document.getElementById('detail-sections');
  sections.innerHTML = '';

  const errDiv = document.createElement('div');
  errDiv.className = 'scan-error';
  errDiv.innerHTML = `⚠️ ${escapeHTML(msg)}`;
  sections.appendChild(errDiv);

  const item = findItemById(config.tree, selectedId);
  if (item) renderNoteSection(item.item, sections);
}

function renderScanResults(data) {
  const sections = document.getElementById('detail-sections');
  sections.innerHTML = '';

  // ─ Metadados ─
  const metaSection = makeSummarySection('📊 Metadados', `
    <div class="meta-row">
      <div class="meta-item">
        <span class="meta-icon">📄</span>
        <span class="meta-value">${escapeHTML(String(data.file_count))}</span>
        <span class="meta-label">arquivos</span>
      </div>
      <div class="meta-item">
        <span class="meta-icon">📁</span>
        <span class="meta-value">${escapeHTML(String(data.dir_count))}</span>
        <span class="meta-label">pastas</span>
      </div>
      <div class="meta-item">
        <span class="meta-icon">💾</span>
        <span class="meta-value">${escapeHTML(formatBytes(data.total_size_bytes))}</span>
      </div>
      ${data.last_modified ? `
      <div class="meta-item">
        <span class="meta-icon">🕐</span>
        <span class="meta-value">${escapeHTML(formatDate(data.last_modified))}</span>
        <span class="meta-label">últ. modificação</span>
      </div>` : ''}
    </div>
  `);
  sections.appendChild(metaSection);

  // ─ Arquivos Recentes ─
  if (data.recent_files && data.recent_files.length > 0) {
    const listHTML = data.recent_files.map(f => `
      <div class="recent-file-item">
        <span class="recent-file-name" title="${escapeHTML(f.name)}">${escapeHTML(f.name)}</span>
        <div class="recent-file-meta">
          <span>${formatDate(f.modified)}</span>
          <span>${formatBytes(f.size_bytes)}</span>
        </div>
      </div>
    `).join('');

    const recentSection = makeSummarySection('🕐 Arquivos Recentes', `<div class="recent-file-list">${listHTML}</div>`);
    sections.appendChild(recentSection);
  }

  // ─ Por Tipo ─
  if (data.by_type && Object.keys(data.by_type).length > 0) {
    const sortedTypes = Object.entries(data.by_type).sort((a, b) => b[1] - a[1]);
    const badgesHTML = sortedTypes.map(([ext, count]) => `
      <span class="type-badge">
        ${escapeHTML(ext.toUpperCase())} <span class="badge-count">${count}</span>
      </span>
    `).join('');

    const typeSection = makeSummarySection('🏷️ Por Tipo', `<div class="type-badges">${badgesHTML}</div>`);
    sections.appendChild(typeSection);
  }

  // Notes last
  const item = findItemById(config.tree, selectedId);
  if (item) renderNoteSection(item.item, sections);
}

// ── Detail label autosave ────────────────────────────────────────────────────
function onDetailLabelBlur(e) {
  const id = e.target.dataset.id;
  const newLabel = e.target.value.trim();
  if (!id || !newLabel) return;

  const found = findItemById(config.tree, id);
  if (found && found.item.label !== newLabel) {
    found.item.label = newLabel;
    saveConfig();
    renderTree();
  }
}

// ── CRUD ─────────────────────────────────────────────────────────────────────
function saveItem(formData) {
  const { id, label, type, path, icon, notes, parentId } = formData;

  if (modalMode === 'edit') {
    const found = findItemById(config.tree, id);
    if (found) {
      Object.assign(found.item, { label, type, path, icon, notes });
      saveConfig();
      renderTree();
      // Re-render detail if this is the selected item
      if (selectedId === id) renderDetailPanel(found.item);
    }
  } else {
    const newItem = {
      id: generateId(),
      type,
      label,
      path: path || '',
      icon: icon || '',
      notes: notes || '',
      pinned: false,
      children: type === 'group' ? [] : undefined,
    };
    // Remove undefined keys
    if (newItem.children === undefined) delete newItem.children;

    if (parentId === null) {
      config.tree.push(newItem);
    } else {
      const found = findItemById(config.tree, parentId);
      if (found) {
        if (!found.item.children) found.item.children = [];
        found.item.children.push(newItem);
        // Auto-expand parent group
        collapsedGroups.delete(parentId);
      }
    }
    saveConfig();
    renderTree();
  }
}

function deleteItem(id) {
  if (!confirm('Excluir este item?')) return;

  removeItemById(config.tree, id);

  if (selectedId === id) {
    selectedId = null;
    document.getElementById('item-detail').style.display = 'none';
    document.getElementById('welcome-state').style.display = '';
  }

  saveConfig();
  renderTree();
}

function togglePin(id) {
  const found = findItemById(config.tree, id);
  if (!found) return;
  found.item.pinned = !found.item.pinned;
  saveConfig();
  renderTree();
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function openModal(mode, parentId, item) {
  modalMode = mode;
  modalParentId = parentId;
  modalEditId = item ? item.id : null;

  const overlay = document.getElementById('modal-overlay');
  const title   = document.getElementById('modal-title');

  // Reset form
  document.getElementById('f-label').value = '';
  document.getElementById('f-path').value  = '';
  document.getElementById('f-icon').value  = '';
  document.getElementById('f-notes').value = '';
  document.querySelector('input[name="f-type"][value="folder"]').checked = true;
  onTypeChange();

  if (mode === 'edit' && item) {
    title.textContent = 'Editar Item';
    document.getElementById('f-label').value = item.label || '';
    document.getElementById('f-path').value  = item.path  || '';
    document.getElementById('f-icon').value  = item.icon  || '';
    document.getElementById('f-notes').value = item.notes || '';
    const radio = document.querySelector(`input[name="f-type"][value="${item.type}"]`);
    if (radio) { radio.checked = true; onTypeChange(); }
  } else {
    title.textContent = 'Novo Item';
  }

  overlay.style.display = 'flex';
  document.getElementById('f-label').focus();
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
}

function onModalSave() {
  const label = document.getElementById('f-label').value.trim();
  if (!label) {
    document.getElementById('f-label').focus();
    return;
  }

  const type  = document.querySelector('input[name="f-type"]:checked').value;
  const path  = document.getElementById('f-path').value.trim();
  const icon  = document.getElementById('f-icon').value.trim();
  const notes = document.getElementById('f-notes').value.trim();

  saveItem({
    id: modalEditId,
    label,
    type,
    path,
    icon,
    notes,
    parentId: modalParentId,
  });

  closeModal();
}

function onTypeChange() {
  const type = document.querySelector('input[name="f-type"]:checked');
  if (!type) return;

  const fgPath  = document.getElementById('fg-path');
  const lblPath = document.getElementById('lbl-path');
  const fPath   = document.getElementById('f-path');

  if (type.value === 'group') {
    fgPath.style.display = 'none';
  } else {
    fgPath.style.display = '';
    if (type.value === 'url') {
      lblPath.textContent = 'URL';
      fPath.placeholder = 'https://...';
    } else {
      lblPath.textContent = 'Caminho';
      fPath.placeholder = 'C:\\caminho\\da\\pasta';
    }
  }
}

// ── Drag & Drop ──────────────────────────────────────────────────────────────
function onDragStart(e, item, parentArray) {
  draggedId = item.id;
  draggedParentRef = parentArray;
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', item.id);
  e.currentTarget.style.opacity = '0.5';
}

function onDragOver(e, li) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  li.classList.add('drag-over');
}

function onDragLeave(li) {
  li.classList.remove('drag-over');
}

function onDrop(e, targetItem, targetParentArray, targetIndex) {
  e.preventDefault();
  e.stopPropagation();

  const li = e.currentTarget;
  li.classList.remove('drag-over');

  if (!draggedId || draggedId === targetItem.id) return;

  // Only reorder within the same parent
  if (draggedParentRef !== targetParentArray) return;

  const fromIndex = targetParentArray.findIndex(i => i.id === draggedId);
  if (fromIndex === -1) return;

  const [removed] = targetParentArray.splice(fromIndex, 1);
  const insertAt  = targetIndex > fromIndex ? targetIndex - 1 : targetIndex;
  targetParentArray.splice(insertAt, 0, removed);

  saveConfig();
  renderTree();
}

function onDragEnd(li) {
  li.style.opacity = '';
  draggedId = null;
  draggedParentRef = null;
  document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
}

// ── Utility ──────────────────────────────────────────────────────────────────
function formatBytes(bytes) {
  if (bytes === 0 || bytes == null) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1) + ' ' + units[i];
}

function formatDate(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now  = new Date();

  const sameDay = (a, b) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);

  if (sameDay(date, now)) {
    return 'Hoje ' + date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  } else if (sameDay(date, yesterday)) {
    return 'Ontem';
  } else {
    return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' });
  }
}

function findItemById(tree, id) {
  for (let i = 0; i < tree.length; i++) {
    const item = tree[i];
    if (item.id === id) return { item, parent: tree, index: i };
    if (item.children && item.children.length > 0) {
      const found = findItemById(item.children, id);
      if (found) return found;
    }
  }
  return null;
}

function removeItemById(tree, id) {
  for (let i = 0; i < tree.length; i++) {
    if (tree[i].id === id) {
      return tree.splice(i, 1)[0];
    }
    if (tree[i].children && tree[i].children.length > 0) {
      const removed = removeItemById(tree[i].children, id);
      if (removed) return removed;
    }
  }
  return null;
}

function generateId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function escapeHTML(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
