/**
 * NavMed — Menu Analyzer Frontend
 * =================================
 * Vanilla JS, sem frameworks. Segue o padrão de app.js.
 */

// ── Estado global ─────────────────────────────────────────────────────────────
let currentMenuId = null
let selectedPhotos = []   // array de File objects
let currentTab = 'analyze'
let compareMode = false
let compareMenuA = null   // menu_id selecionado para comparação
let processingTimer = null

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupDropzone()
  setupFileInput()
  setupHistorySearch()
})

// ── Tabs ──────────────────────────────────────────────────────────────────────
function switchTab(tab) {
  currentTab = tab
  document.getElementById('tab-analyze').style.display = tab === 'analyze' ? '' : 'none'
  document.getElementById('tab-history').style.display = tab === 'history' ? '' : 'none'
  document.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab)
  })
  if (tab === 'history') loadHistory()
}

// ── Dropzone ──────────────────────────────────────────────────────────────────
function setupDropzone() {
  const dz = document.getElementById('dropzone')
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag-over') })
  dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'))
  dz.addEventListener('drop', e => {
    e.preventDefault()
    dz.classList.remove('drag-over')
    addPhotos(Array.from(e.dataTransfer.files))
  })
}

function setupFileInput() {
  document.getElementById('file-input').addEventListener('change', e => {
    addPhotos(Array.from(e.target.files))
    e.target.value = ''
  })
}

function addPhotos(files) {
  const allowed = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
  for (const f of files) {
    if (!allowed.includes(f.type)) {
      showToast(`Arquivo "${f.name}" não suportado. Use JPEG, PNG ou WebP.`, 'error')
      continue
    }
    if (f.size > 5 * 1024 * 1024) {
      showToast(`"${f.name}" excede 5 MB.`, 'error')
      continue
    }
    if (selectedPhotos.length >= 5) {
      showToast('Máximo de 5 fotos permitidas.', 'error')
      break
    }
    selectedPhotos.push(f)
  }
  renderThumbnails()
  updateAnalyzeButton()
}

function removePhoto(idx) {
  selectedPhotos.splice(idx, 1)
  renderThumbnails()
  updateAnalyzeButton()
}

function renderThumbnails() {
  const strip = document.getElementById('thumbnail-strip')
  strip.innerHTML = selectedPhotos.map((f, i) => {
    const url = URL.createObjectURL(f)
    return `<div class="thumb-card">
      <img src="${url}" alt="${escapeHTML(f.name)}">
      <button class="thumb-remove" onclick="removePhoto(${i})" title="Remover">✕</button>
    </div>`
  }).join('')
}

function updateAnalyzeButton() {
  document.getElementById('btn-analyze').disabled = selectedPhotos.length === 0
}

// ── Análise ───────────────────────────────────────────────────────────────────
async function submitAnalysis() {
  if (selectedPhotos.length === 0) return

  const restaurantName = document.getElementById('restaurant-name').value.trim()
  const locationNotes  = document.getElementById('location-notes').value.trim()
  const saveHistory    = document.getElementById('save-to-history').checked

  showProcessingState()

  const formData = new FormData()
  selectedPhotos.forEach(f => formData.append('photos[]', f))
  formData.append('restaurant_name', restaurantName)
  formData.append('location_notes', locationNotes)
  formData.append('save', saveHistory ? 'true' : 'false')

  try {
    const res = await fetch('/api/menus/analyze', { method: 'POST', body: formData })
    const data = await res.json()
    if (!res.ok || !data.ok) {
      throw new Error(data.error || 'Erro desconhecido na análise.')
    }
    currentMenuId = data.menu_id
    showResultsState(data)
  } catch (err) {
    showUploadState()
    showToast(err.message, 'error')
  }
}

function showProcessingState() {
  document.getElementById('state-upload').style.display = 'none'
  document.getElementById('state-processing').style.display = ''
  document.getElementById('state-results').style.display = 'none'

  const messages = [
    'Enviando fotos...',
    'Claude está analisando o cardápio...',
    'Identificando pratos e preços...',
    'Calculando estimativas nutricionais...',
    'Gerando recomendações inteligentes...',
    'Finalizando análise...',
  ]
  let idx = 0
  const el = document.getElementById('processing-status')
  el.textContent = messages[0]
  processingTimer = setInterval(() => {
    idx = (idx + 1) % messages.length
    el.textContent = messages[idx]
  }, 2500)
}

function showUploadState() {
  clearInterval(processingTimer)
  document.getElementById('state-upload').style.display = ''
  document.getElementById('state-processing').style.display = 'none'
  document.getElementById('state-results').style.display = 'none'
}

function resetToUpload() {
  currentMenuId = null
  selectedPhotos = []
  renderThumbnails()
  updateAnalyzeButton()
  document.getElementById('restaurant-name').value = ''
  document.getElementById('location-notes').value = ''
  document.getElementById('save-to-history').checked = true
  showUploadState()
}

function showResultsState(data) {
  clearInterval(processingTimer)
  document.getElementById('state-upload').style.display = 'none'
  document.getElementById('state-processing').style.display = 'none'
  document.getElementById('state-results').style.display = ''

  const summary    = data.summary || {}
  const categories = data.categories || []

  document.getElementById('results-summary-bar').innerHTML =
    buildSection('📊 Resumo', renderSummaryBar(summary, data))

  document.getElementById('results-highlights').innerHTML =
    buildSection('⭐ Destaques', renderHighlights(summary.highlights || {}, categories))

  document.getElementById('results-price-intel').innerHTML =
    buildSection('💰 Inteligência de Preços', renderPriceIntelligence(summary))

  document.getElementById('results-categories').innerHTML =
    buildSection('🍽️ Cardápio Completo', renderCategories(categories), false)

  document.getElementById('results-allergen-map').innerHTML =
    buildSection('⚠️ Mapa de Alérgenos', renderAllergenMap(summary.allergen_counts || {}))

  document.getElementById('results-raw-analysis').innerHTML =
    buildSection('🤖 Análise Claude', renderRawAnalysis(data.raw_analysis || ''))

  // Attach section toggle listeners
  document.querySelectorAll('.section-header').forEach(h => {
    h.addEventListener('click', () => {
      const body    = h.nextElementSibling
      const chevron = h.querySelector('.section-chevron')
      const open    = body.style.display !== 'none'
      body.style.display = open ? 'none' : ''
      if (chevron) chevron.classList.toggle('open', !open)
    })
  })

  // Attach category toggles
  document.querySelectorAll('.category-header').forEach(h => {
    h.addEventListener('click', () => {
      const body = h.nextElementSibling
      body.style.display = body.style.display === 'none' ? '' : 'none'
    })
  })
}

// ── Renderização de resultados ────────────────────────────────────────────────
function buildSection(title, bodyHTML, startOpen = true) {
  return `<div class="results-section">
    <div class="section-header">
      <span class="section-title">${title}</span>
      <span class="section-chevron ${startOpen ? 'open' : ''}">▼</span>
    </div>
    <div class="section-body" ${startOpen ? '' : 'style="display:none"'}>
      ${bodyHTML}
    </div>
  </div>`
}

function renderSummaryBar(summary, data) {
  const chips = []
  if (summary.price_range_label)
    chips.push(`<span class="chip chip-price">${summary.price_range} ${summary.price_range_label}</span>`)
  if (summary.total_items)
    chips.push(`<span class="chip" style="background:var(--bg-deep);color:var(--muted)">${summary.total_items} pratos</span>`)
  if (data.restaurant_name && data.restaurant_name !== 'Restaurante sem nome')
    chips.push(`<span class="chip" style="background:var(--bg-deep);color:var(--muted)">🏠 ${escapeHTML(data.restaurant_name)}</span>`)

  const dc = summary.dietary_counts || {}
  if (dc.vegan)
    chips.push(`<span class="chip chip-vegan">🌱 ${dc.vegan} veganos</span>`)
  if (dc.vegetarian)
    chips.push(`<span class="chip chip-veg">🥗 ${dc.vegetarian} vegetarianos</span>`)

  const ac = summary.allergen_counts || {}
  const allergenChips = {
    gluten: 'chip-gluten', lactose: 'chip-lactose', nuts: 'chip-nuts',
    shellfish: 'chip-shellfish', eggs: 'chip-eggs', soy: 'chip-soy',
  }
  const allergenLabels = {
    gluten: '🌾 Glúten', lactose: '🥛 Lactose', nuts: '🥜 Nozes',
    shellfish: '🦐 Frutos do mar', eggs: '🥚 Ovos', soy: '🫘 Soja',
  }
  for (const [k, cls] of Object.entries(allergenChips)) {
    if (ac[k]) chips.push(`<span class="chip ${cls}">${allergenLabels[k]}: ${ac[k]}</span>`)
  }

  return `<div class="summary-chips">${chips.join('')}</div>`
}

function renderHighlights(highlights, categories) {
  const BADGE_META = {
    best_value:   { icon: '💰', label: 'Melhor Custo-Benefício' },
    chefs_choice: { icon: '👨‍🍳', label: 'Escolha do Chef' },
    healthy_pick: { icon: '🥗', label: 'Opção Saudável' },
  }

  // Build price lookup
  const priceMap = {}
  for (const cat of categories) {
    for (const item of cat.items || []) {
      priceMap[item.id] = item.price_raw || formatCurrency(item.price)
    }
  }

  let html = '<div class="highlights-grid">'
  for (const [key, meta] of Object.entries(BADGE_META)) {
    const h = highlights[key]
    if (h) {
      html += `<div class="highlight-card">
        <div class="highlight-icon">${meta.icon}</div>
        <div class="highlight-label">${meta.label}</div>
        <div class="highlight-name">${escapeHTML(h.item_name || '')}</div>
        <div class="highlight-price">${priceMap[h.item_id] || ''}</div>
      </div>`
    }
  }

  const combo = highlights.popular_combo
  if (combo && combo.length >= 2) {
    const names = combo.slice(0, 2).map(c => escapeHTML(c.item_name || '')).join(' + ')
    html += `<div class="highlight-card">
      <div class="highlight-icon">⭐</div>
      <div class="highlight-label">Combo Popular</div>
      <div class="highlight-name">${names}</div>
    </div>`
  }

  html += '</div>'
  return html
}

function renderPriceIntelligence(summary) {
  const fmt = v => (v != null ? formatCurrency(v) : '—')
  return `<div class="price-grid">
    <div class="price-stat">
      <div class="price-stat-label">Mínimo</div>
      <div class="price-stat-value price-min-val">${fmt(summary.price_min)}</div>
    </div>
    <div class="price-stat">
      <div class="price-stat-label">Média</div>
      <div class="price-stat-value price-avg-val">${fmt(summary.price_avg)}</div>
    </div>
    <div class="price-stat">
      <div class="price-stat-label">Máximo</div>
      <div class="price-stat-value price-max-val">${fmt(summary.price_max)}</div>
    </div>
  </div>`
}

function renderCategories(categories) {
  if (!categories.length) return '<p style="color:var(--muted)">Nenhuma categoria encontrada.</p>'
  return categories.map(cat => {
    const items = (cat.items || []).map(renderDishRow).join('')
    return `<div class="category-section">
      <div class="category-header">
        <span>${escapeHTML(cat.name || 'Sem nome')}</span>
        <span class="category-count">${(cat.items || []).length} pratos</span>
      </div>
      <div class="category-items">${items}</div>
    </div>`
  }).join('')
}

function renderDishRow(item) {
  const allergenLabels = {
    gluten: '🌾 Glúten', lactose: '🥛 Lactose', nuts: '🥜 Nozes',
    shellfish: '🦐 Frutos do mar', eggs: '🥚 Ovos', soy: '🫘 Soja',
  }
  const tagLabels = { vegetarian: 'Vegetariano', vegan: 'Vegano' }
  const badgeLabels = {
    best_value: '💰 Melhor Valor', chefs_choice: '👨‍🍳 Chef', healthy_pick: '🥗 Saudável',
  }

  const allergenTags = (item.allergens || []).map(a =>
    `<span class="dish-tag tag-allergen">${allergenLabels[a] || a}</span>`
  ).join('')

  const itemTags = (item.tags || []).map(t =>
    `<span class="dish-tag tag-${t}">${tagLabels[t] || t}</span>`
  ).join('')

  const badgeTags = (item.badges || []).filter(b => b !== 'popular_combo').map(b =>
    `<span class="dish-tag tag-badge">${badgeLabels[b] || b}</span>`
  ).join('')

  const stars = renderStars(item.value_score)
  const cal = item.calories_estimate ? `~${item.calories_estimate} kcal` : ''
  const price = item.price_raw || formatCurrency(item.price)

  return `<div class="dish-row">
    <div class="dish-info">
      <div class="dish-name">${escapeHTML(item.name || '')}</div>
      ${item.description ? `<div class="dish-desc">${escapeHTML(item.description)}</div>` : ''}
      <div class="dish-meta">${allergenTags}${itemTags}${badgeTags}</div>
    </div>
    <div class="dish-right">
      <div class="dish-price">${price || '—'}</div>
      ${cal ? `<div class="dish-cal">${cal}</div>` : ''}
      ${stars ? `<div class="value-stars">${stars}</div>` : ''}
    </div>
  </div>`
}

function renderStars(score) {
  if (score == null) return ''
  const full  = Math.round(score / 2)
  const stars = '★'.repeat(Math.min(5, full)) + '☆'.repeat(Math.max(0, 5 - full))
  return stars
}

function renderAllergenMap(allergenCounts) {
  const ALLERGENS = {
    gluten:    { icon: '🌾', label: 'Glúten' },
    lactose:   { icon: '🥛', label: 'Lactose' },
    nuts:      { icon: '🥜', label: 'Nozes' },
    shellfish: { icon: '🦐', label: 'Frutos do mar' },
    eggs:      { icon: '🥚', label: 'Ovos' },
    soy:       { icon: '🫘', label: 'Soja' },
  }
  const entries = Object.entries(ALLERGENS).filter(([k]) => allergenCounts[k] > 0)
  if (!entries.length) {
    return '<p style="color:var(--muted)">Nenhum alérgeno identificado.</p>'
  }
  return `<div class="allergen-grid">${
    entries.map(([k, { icon, label }]) => `
      <div class="allergen-card">
        <div class="allergen-icon">${icon}</div>
        <div class="allergen-name">${label}</div>
        <div class="allergen-count">${allergenCounts[k]}</div>
        <div style="color:var(--muted);font-size:11px">pratos</div>
      </div>`
    ).join('')
  }</div>`
}

function renderRawAnalysis(text) {
  if (!text) return '<p style="color:var(--muted)">Análise narrativa não disponível.</p>'
  return `<p class="raw-analysis-text">${escapeHTML(text)}</p>`
}

// ── Export ────────────────────────────────────────────────────────────────────
async function exportCurrentMenu() {
  if (!currentMenuId) return
  try {
    const res = await fetch(`/api/menus/${currentMenuId}/export`, { method: 'POST' })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error)
    window.open(data.url, '_blank')
    showToast('Cardápio exportado! Abrindo em nova aba.', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function exportMenu(menuId) {
  try {
    const res = await fetch(`/api/menus/${menuId}/export`, { method: 'POST' })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error)
    window.open(data.url, '_blank')
    showToast('Cardápio exportado!', 'success')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

// ── Histórico ─────────────────────────────────────────────────────────────────
let historyDebounceTimer = null

function setupHistorySearch() {
  const el = document.getElementById('history-search')
  if (!el) return
  el.addEventListener('input', () => {
    clearTimeout(historyDebounceTimer)
    historyDebounceTimer = setTimeout(() => loadHistory(el.value), 300)
  })
}

async function loadHistory(q = '') {
  const listEl = document.getElementById('history-list')
  listEl.innerHTML = '<div style="color:var(--muted);padding:20px">Carregando...</div>'
  try {
    const qs = q ? `?q=${encodeURIComponent(q)}` : ''
    const res = await fetch(`/api/menus/history${qs}`)
    const data = await res.json()
    renderHistoryList(data.menus || [])
  } catch {
    listEl.innerHTML = '<div style="color:var(--danger);padding:20px">Erro ao carregar histórico.</div>'
  }
}

function renderHistoryList(menus) {
  const listEl = document.getElementById('history-list')
  if (!menus.length) {
    listEl.innerHTML = `<div class="empty-state">
      <div class="empty-icon">📭</div>
      <div class="empty-title">Nenhum cardápio salvo ainda</div>
      <div>Analise um cardápio e salve no histórico</div>
    </div>`
    return
  }

  listEl.innerHTML = menus.map(m => {
    const date    = formatDate(m.analyzed_at)
    const photos  = `${m.photo_count || 1} foto${m.photo_count !== 1 ? 's' : ''}`
    const isSelA  = compareMode && compareMenuA === m.menu_id

    return `<div class="history-card${compareMode ? ' compare-selecting' : ''}${isSelA ? ' compare-selected-a' : ''}"
               onclick="${compareMode ? `selectForCompare('${m.menu_id}')` : ''}">
      <div class="history-icon">🍽️</div>
      <div class="history-info">
        <div class="history-name">${escapeHTML(m.restaurant_name || 'Sem nome')}</div>
        <div class="history-meta">${date} · ${photos}${m.location_notes ? ' · ' + escapeHTML(m.location_notes) : ''}</div>
        <div class="history-chips">
          ${m.price_range ? `<span class="chip chip-price">${m.price_range}</span>` : ''}
          ${m.total_items ? `<span class="chip" style="background:var(--bg-deep);color:var(--muted)">${m.total_items} pratos</span>` : ''}
        </div>
      </div>
      <div class="history-actions" onclick="event.stopPropagation()">
        <button class="btn btn-secondary btn-sm" onclick="viewMenu('${m.menu_id}')">👁 Ver</button>
        <button class="btn btn-secondary btn-sm" onclick="exportMenu('${m.menu_id}')">⬇ Exportar</button>
        <button class="btn btn-secondary btn-sm" onclick="startCompare('${m.menu_id}')">⚖ Comparar</button>
        <button class="btn btn-danger btn-sm" onclick="deleteMenu('${m.menu_id}')">🗑 Deletar</button>
      </div>
    </div>`
  }).join('')
}

async function viewMenu(menuId) {
  try {
    const res = await fetch(`/api/menus/${menuId}`)
    const data = await res.json()
    if (!data.ok) throw new Error(data.error)
    currentMenuId = data.menu_id
    switchTab('analyze')
    showResultsState(data)
  } catch (err) {
    showToast(err.message, 'error')
  }
}

async function deleteMenu(menuId) {
  if (!confirm('Remover este cardápio do histórico?')) return
  try {
    const res = await fetch(`/api/menus/${menuId}`, { method: 'DELETE' })
    const data = await res.json()
    if (!data.ok) throw new Error(data.error)
    showToast('Cardápio removido.', 'info')
    loadHistory(document.getElementById('history-search').value)
  } catch (err) {
    showToast(err.message, 'error')
  }
}

// ── Comparação ────────────────────────────────────────────────────────────────
function startCompare(menuId) {
  compareMode = true
  compareMenuA = menuId
  document.getElementById('compare-banner').style.display = ''
  document.getElementById('compare-banner-text').textContent =
    'Cardápio A selecionado. Agora selecione o segundo cardápio.'
  document.getElementById('compare-view').style.display = 'none'
  loadHistory(document.getElementById('history-search').value)
}

async function selectForCompare(menuId) {
  if (!compareMode) return
  if (menuId === compareMenuA) {
    showToast('Selecione um cardápio diferente para comparar.', 'error')
    return
  }
  compareMode = false
  document.getElementById('compare-banner').style.display = 'none'

  try {
    const res = await fetch(`/api/menus/compare?a=${compareMenuA}&b=${menuId}`)
    const data = await res.json()
    if (!data.ok) throw new Error(data.error)
    renderCompareView(data)
  } catch (err) {
    showToast(err.message, 'error')
  }
}

function cancelCompare() {
  compareMode = false
  compareMenuA = null
  document.getElementById('compare-banner').style.display = 'none'
  document.getElementById('compare-view').style.display = 'none'
  loadHistory(document.getElementById('history-search').value)
}

function closeCompareView() {
  document.getElementById('compare-view').style.display = 'none'
  document.getElementById('history-list').style.display = ''
}

function renderCompareView(data) {
  const a    = data.a
  const b    = data.b
  const diff = data.diff || {}

  document.getElementById('history-list').style.display = 'none'
  const cv = document.getElementById('compare-view')
  cv.style.display = ''

  const diffSign = v => v > 0 ? `+${v}` : v < 0 ? `${v}` : '0'
  const diffClass = v => v > 0 ? 'diff-positive' : v < 0 ? 'diff-negative' : 'diff-neutral'

  const colHTML = (menu) => {
    const sum = menu.summary || {}
    return `<div class="compare-col">
      <div class="compare-col-title">🍽️ ${escapeHTML(menu.restaurant_name || 'Sem nome')}</div>
      <div class="compare-stat"><span class="compare-stat-label">Faixa de preço</span><span>${sum.price_range_label || '—'}</span></div>
      <div class="compare-stat"><span class="compare-stat-label">Preço médio</span><span style="color:var(--accent)">${formatCurrency(sum.price_avg)}</span></div>
      <div class="compare-stat"><span class="compare-stat-label">Preço mínimo</span><span style="color:var(--success)">${formatCurrency(sum.price_min)}</span></div>
      <div class="compare-stat"><span class="compare-stat-label">Preço máximo</span><span style="color:var(--danger)">${formatCurrency(sum.price_max)}</span></div>
      <div class="compare-stat"><span class="compare-stat-label">Total de pratos</span><span>${sum.total_items || 0}</span></div>
      <div class="compare-stat"><span class="compare-stat-label">Veganos</span><span>${(sum.dietary_counts || {}).vegan || 0}</span></div>
      <div class="compare-stat"><span class="compare-stat-label">Vegetarianos</span><span>${(sum.dietary_counts || {}).vegetarian || 0}</span></div>
      <div style="margin-top:12px;display:flex;gap:6px;flex-wrap:wrap">
        <button class="btn btn-sm btn-secondary" onclick="viewMenu('${menu.menu_id}')">👁 Ver completo</button>
        <button class="btn btn-sm btn-secondary" onclick="exportMenu('${menu.menu_id}')">⬇ Exportar</button>
      </div>
    </div>`
  }

  document.getElementById('compare-grid').innerHTML = `
    ${colHTML(a)}
    <div class="compare-diff">
      <div class="diff-item">
        <div class="diff-label">Preço médio</div>
        <div class="diff-val ${diffClass(diff.price_avg_diff)}">${diffSign(diff.price_avg_diff)}</div>
      </div>
      <div class="diff-item">
        <div class="diff-label">Pratos</div>
        <div class="diff-val ${diffClass(diff.items_diff)}">${diffSign(diff.items_diff)}</div>
      </div>
      <div class="diff-item">
        <div class="diff-label">Veganos</div>
        <div class="diff-val ${diffClass(diff.vegan_diff)}">${diffSign(diff.vegan_diff)}</div>
      </div>
      <div class="diff-item">
        <div class="diff-label">Vegetarianos</div>
        <div class="diff-val ${diffClass(diff.vegetarian_diff)}">${diffSign(diff.vegetarian_diff)}</div>
      </div>
    </div>
    ${colHTML(b)}`
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container')
  const toast = document.createElement('div')
  toast.className = `toast toast-${type}`
  toast.textContent = msg
  container.appendChild(toast)
  setTimeout(() => {
    toast.style.opacity = '0'
    toast.style.transition = 'opacity 0.3s'
    setTimeout(() => toast.remove(), 300)
  }, 4000)
}

// ── Utilitários (espelham app.js) ─────────────────────────────────────────────
function escapeHTML(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function formatCurrency(value) {
  if (value == null) return '—'
  return 'R$ ' + Number(value).toFixed(2).replace('.', ',')
}

function formatDate(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch {
    return iso.slice(0, 10)
  }
}
