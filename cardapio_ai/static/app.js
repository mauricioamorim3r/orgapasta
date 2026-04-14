let currentMenuId = null
let selectedPhotos = []
let currentTab = 'analyze'
let compareMode = false
let compareMenuA = null
let processingTimer = null
let historyDebounceTimer = null

const PROVIDER_META = {
  claude: { label: 'Claude Sonnet', hint: 'Claude esta analisando o cardapio.' },
  openai: { label: 'GPT-4o', hint: 'GPT-4o esta analisando o cardapio.' },
  gemini: { label: 'Gemini 2.0 Flash', hint: 'Gemini esta analisando o cardapio.' },
  groq: { label: 'Llama 4 Scout', hint: 'Llama 4 Scout esta analisando o cardapio.' },
}

const SPICE_LABELS = {
  none: 'Sem picancia',
  mild: 'Picancia leve',
  medium: 'Picancia media',
  hot: 'Picancia alta',
  unknown: 'Picancia nao identificada',
}

document.addEventListener('DOMContentLoaded', () => {
  setupDropzone()
  setupFileInput()
  setupHistorySearch()
})

function switchTab(tab) {
  currentTab = tab
  document.getElementById('tab-analyze').hidden = tab !== 'analyze'
  document.getElementById('tab-history').hidden = tab !== 'history'
  document.querySelectorAll('.tab-btn').forEach((button) => {
    button.classList.toggle('active', button.dataset.tab === tab)
  })
  if (tab === 'history') {
    loadHistory(document.getElementById('history-search').value)
  }
}

function setupDropzone() {
  const dropzone = document.getElementById('dropzone')
  const fileInput = document.getElementById('file-input')

  dropzone.addEventListener('click', () => fileInput.click())
  dropzone.addEventListener('dragover', (event) => {
    event.preventDefault()
    dropzone.classList.add('drag-over')
  })
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'))
  dropzone.addEventListener('drop', (event) => {
    event.preventDefault()
    dropzone.classList.remove('drag-over')
    addPhotos(Array.from(event.dataTransfer.files))
  })
}

function setupFileInput() {
  document.getElementById('file-input').addEventListener('change', (event) => {
    addPhotos(Array.from(event.target.files))
    event.target.value = ''
  })
}

function setupHistorySearch() {
  const searchInput = document.getElementById('history-search')
  searchInput.addEventListener('input', () => {
    clearTimeout(historyDebounceTimer)
    historyDebounceTimer = setTimeout(() => loadHistory(searchInput.value.trim()), 300)
  })
}

function addPhotos(files) {
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
  for (const file of files) {
    if (!allowedTypes.includes(file.type)) {
      showToast(`Arquivo ${file.name} nao suportado.`, 'error')
      continue
    }
    if (file.size > 5 * 1024 * 1024) {
      showToast(`${file.name} excede 5 MB.`, 'error')
      continue
    }
    if (selectedPhotos.length >= 5) {
      showToast('Maximo de 5 fotos permitido.', 'error')
      break
    }
    selectedPhotos.push(file)
  }
  renderThumbnails()
  updateAnalyzeButton()
}

function removePhoto(index) {
  selectedPhotos.splice(index, 1)
  renderThumbnails()
  updateAnalyzeButton()
}

function renderThumbnails() {
  const strip = document.getElementById('thumbnail-strip')
  strip.innerHTML = selectedPhotos.map((file, index) => {
    const url = URL.createObjectURL(file)
    return `<div class="thumb-card">
      <img src="${url}" alt="${escapeHTML(file.name)}">
      <button class="thumb-remove" type="button" onclick="removePhoto(${index})" aria-label="Remover foto">x</button>
    </div>`
  }).join('')
}

function updateAnalyzeButton() {
  document.getElementById('btn-analyze').disabled = selectedPhotos.length === 0
}

async function submitAnalysis() {
  if (!selectedPhotos.length) {
    return
  }

  const restaurantName = document.getElementById('restaurant-name').value.trim()
  const locationNotes = document.getElementById('location-notes').value.trim()
  const saveToHistory = document.getElementById('save-to-history').checked
  const providerEl = document.querySelector('[name="provider"]:checked')
  const provider = providerEl ? providerEl.value : 'claude'

  showProcessingState(provider)

  const formData = new FormData()
  selectedPhotos.forEach((file) => formData.append('photos[]', file))
  formData.append('restaurant_name', restaurantName)
  formData.append('location_notes', locationNotes)
  formData.append('save', saveToHistory ? 'true' : 'false')
  formData.append('provider', provider)

  try {
    const response = await fetch('/api/menus/analyze', { method: 'POST', body: formData })
    const data = await response.json()
    if (!response.ok || !data.ok) {
      throw new Error(data.error || 'Erro ao analisar cardapio.')
    }
    currentMenuId = data.menu_id
    showResultsState(data)
  } catch (error) {
    showUploadState()
    showToast(error.message, 'error')
  }
}

function showProcessingState(provider) {
  const meta = PROVIDER_META[provider] || PROVIDER_META.claude
  document.getElementById('state-upload').hidden = true
  document.getElementById('state-processing').hidden = false
  document.getElementById('state-results').hidden = true
  document.getElementById('processing-model').textContent = meta.hint

  const messages = [
    'Enviando fotos...',
    `${meta.label} esta lendo os pratos...`,
    'Identificando categorias e precos...',
    'Estimando calorias e alergenos...',
    'Gerando destaques do cardapio...',
  ]

  let index = 0
  const status = document.getElementById('processing-status')
  status.textContent = messages[0]
  clearInterval(processingTimer)
  processingTimer = setInterval(() => {
    index = (index + 1) % messages.length
    status.textContent = messages[index]
  }, 2200)
}

function showUploadState() {
  clearInterval(processingTimer)
  document.getElementById('state-upload').hidden = false
  document.getElementById('state-processing').hidden = true
  document.getElementById('state-results').hidden = true
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
  document.getElementById('state-upload').hidden = true
  document.getElementById('state-processing').hidden = true
  document.getElementById('state-results').hidden = false

  const summary = data.summary || {}
  const categories = data.categories || []

  document.getElementById('results-photo-gallery').innerHTML =
    buildSection('Fotos da analise', renderPhotoGallery(data.photo_files || []))

  document.getElementById('results-summary-bar').innerHTML =
    buildSection('Resumo', renderSummaryBar(summary, data))

  document.getElementById('results-insights').innerHTML =
    buildSection('Leitura expandida', renderInsights(summary))

  document.getElementById('results-highlights').innerHTML =
    buildSection('Destaques', renderHighlights(summary.highlights || {}, categories))

  document.getElementById('results-price-intel').innerHTML =
    buildSection('Inteligencia de precos', renderPriceIntelligence(summary))

  document.getElementById('results-categories').innerHTML =
    buildSection('Cardapio completo', renderCategories(categories), false)

  document.getElementById('results-allergen-map').innerHTML =
    buildSection('Mapa de alergenos', renderAllergenMap(summary.allergen_counts || {}))

  document.getElementById('results-raw-analysis').innerHTML =
    buildSection('Analise narrativa', renderRawAnalysis(data.raw_analysis || ''))

  document.querySelectorAll('.section-header').forEach((header) => {
    header.addEventListener('click', () => {
      const body = header.nextElementSibling
      const chevron = header.querySelector('.section-chevron')
      const isOpen = body.style.display !== 'none'
      body.style.display = isOpen ? 'none' : ''
      if (chevron) {
        chevron.classList.toggle('open', !isOpen)
      }
    })
  })

  document.querySelectorAll('.category-header').forEach((header) => {
    header.addEventListener('click', () => {
      const body = header.nextElementSibling
      body.style.display = body.style.display === 'none' ? '' : 'none'
    })
  })
}

function buildSection(title, bodyHtml, startOpen = true) {
  return `<div class="result-section">
    <div class="section-header">
      <span class="section-title">${title}</span>
      <span class="section-chevron ${startOpen ? 'open' : ''}">v</span>
    </div>
    <div class="section-body" ${startOpen ? '' : 'style="display:none"'}>
      ${bodyHtml}
    </div>
  </div>`
}

function renderSummaryBar(summary, data) {
  const chips = []
  if (summary.price_range_label) {
    chips.push(`<span class="chip">${escapeHTML(summary.price_range || '')} ${escapeHTML(summary.price_range_label)}</span>`)
  }
  if (summary.total_items) {
    chips.push(`<span class="chip">${summary.total_items} pratos</span>`)
  }
  if (data.restaurant_name && data.restaurant_name !== 'Restaurante sem nome') {
    chips.push(`<span class="chip">${escapeHTML(data.restaurant_name)}</span>`)
  }
  if (data.model_used) {
    chips.push(`<span class="badge-model-used">${escapeHTML(data.model_used)}</span>`)
  }

  const dietaryCounts = summary.dietary_counts || {}
  if (dietaryCounts.vegan) {
    chips.push(`<span class="chip">Vegan: ${dietaryCounts.vegan}</span>`)
  }
  if (dietaryCounts.vegetarian) {
    chips.push(`<span class="chip">Vegetarian: ${dietaryCounts.vegetarian}</span>`)
  }
  if (dietaryCounts.gluten_free) {
    chips.push(`<span class="chip">Gluten free: ${dietaryCounts.gluten_free}</span>`)
  }

  if (summary.detected_currency) {
    chips.push(`<span class="chip">Moeda: ${escapeHTML(summary.detected_currency)}</span>`)
  }
  ;(summary.languages_detected || []).forEach((language) => {
    chips.push(`<span class="chip">Idioma: ${escapeHTML(language)}</span>`)
  })
  ;(summary.cuisine_hints || []).forEach((cuisine) => {
    chips.push(`<span class="chip">Culinaria: ${escapeHTML(cuisine)}</span>`)
  })

  const allergenCounts = summary.allergen_counts || {}
  const allergenLabels = {

function renderPhotoGallery(photoFiles) {
  if (!photoFiles.length) {
    return '<div class="empty-state">Nenhuma foto registrada.</div>'
  }
  return `<div class="photo-grid">${photoFiles.map((photo, index) => `
    <figure class="photo-card">
      <img src="${photo.url}" alt="Foto ${index + 1} do cardapio" class="analysis-photo">
      <figcaption class="photo-caption">${escapeHTML(photo.original_name || photo.filename || `Foto ${index + 1}`)}</figcaption>
    </figure>
  `).join('')}</div>`
}

function renderInsights(summary) {
  const blocks = []
  const warnings = summary.warnings || []
  const cuisines = summary.cuisine_hints || []
  const languages = summary.languages_detected || []
  const combos = summary.combo_suggestions || []

  if (warnings.length) {
    blocks.push(`<div class="insight-card"><div class="insight-title">Avisos de leitura</div><ul>${warnings.map((warning) => `<li>${escapeHTML(warning)}</li>`).join('')}</ul></div>`)
  }
  if (cuisines.length || languages.length) {
    blocks.push(`<div class="insight-card"><div class="insight-title">Contexto detectado</div><p>${cuisines.length ? `Culinaria: ${escapeHTML(cuisines.join(', '))}. ` : ''}${languages.length ? `Idiomas: ${escapeHTML(languages.join(', '))}.` : ''}</p></div>`)
  }
  if (combos.length) {
    blocks.push(`<div class="insight-card"><div class="insight-title">Combos sugeridos</div>${combos.map((combo) => `<div class="combo-row"><strong>${escapeHTML(combo.title || 'Combo')}</strong><span>${escapeHTML((combo.items || []).join(' + '))}</span><small>${escapeHTML(combo.reason || '')}${combo.total_price != null ? ` · ${formatCurrency(combo.total_price)}` : ''}</small></div>`).join('')}</div>`)
  }

  if (!blocks.length) {
    return '<div class="empty-state">Nenhum insight adicional retornado pelo modelo.</div>'
  }
  return `<div class="insight-grid">${blocks.join('')}</div>`
}
    gluten: 'Gluten',
    lactose: 'Lactose',
    nuts: 'Nuts',
    shellfish: 'Shellfish',
    eggs: 'Eggs',
    soy: 'Soy',
  }
  Object.entries(allergenLabels).forEach(([key, label]) => {
    if (allergenCounts[key]) {
      chips.push(`<span class="chip">${label}: ${allergenCounts[key]}</span>`)
    }
  })
  return `<div class="summary-chips">${chips.join('')}</div>`
}

function renderHighlights(highlights, categories) {
  const badgeMeta = {
    best_value: { label: 'Best value' },
    chefs_choice: { label: 'Chef choice' },
    healthy_pick: { label: 'Healthy pick' },
  }

  const priceMap = {}
  categories.forEach((category) => {
    ;(category.items || []).forEach((item) => {
      priceMap[item.id] = item.price_raw || formatCurrency(item.price)
    })
  })

  let html = '<div class="highlights-grid">'
  Object.entries(badgeMeta).forEach(([key, meta]) => {
    const item = highlights[key]
    if (!item) {
      return
    }
    html += `<div class="highlight-card">
      <div class="highlight-label">${meta.label}</div>
      <div class="highlight-name">${escapeHTML(item.item_name || '')}</div>
      <div class="highlight-price">${priceMap[item.item_id] || ''}</div>
    </div>`
  })

  const combo = highlights.popular_combo
  if (combo && combo.length >= 2) {
    const names = combo.slice(0, 2).map((item) => escapeHTML(item.item_name || '')).join(' + ')
    html += `<div class="highlight-card">
      <div class="highlight-label">Popular combo</div>
      <div class="highlight-name">${names}</div>
    </div>`
  }

  html += '</div>'
  return html
}

function renderPriceIntelligence(summary) {
  return `<div class="price-grid">
    <div class="price-stat">
      <div class="price-stat-label">Minimo</div>
      <div class="price-stat-value price-min-val">${formatCurrency(summary.price_min)}</div>
    </div>
    <div class="price-stat">
      <div class="price-stat-label">Media</div>
      <div class="price-stat-value price-avg-val">${formatCurrency(summary.price_avg)}</div>
    </div>
    <div class="price-stat">
      <div class="price-stat-label">Maximo</div>
      <div class="price-stat-value price-max-val">${formatCurrency(summary.price_max)}</div>
    </div>
  </div>`
}

function renderCategories(categories) {
  if (!categories.length) {
    return '<div class="empty-state">Nenhuma categoria encontrada.</div>'
  }
  return categories.map((category) => {
    const items = (category.items || []).map(renderDishRow).join('')
    return `<div class="category-section">
      <div class="category-header">
        <span>${escapeHTML(category.name || 'Sem nome')}</span>
        <span class="category-count">${(category.items || []).length} pratos</span>
      </div>
      <div class="category-items">${items}</div>
    </div>`
  }).join('')
}

function renderDishRow(item) {
  const allergenLabels = {
    gluten: 'Gluten',
    lactose: 'Lactose',
    nuts: 'Nuts',
    shellfish: 'Shellfish',
    eggs: 'Eggs',
    soy: 'Soy',
  }
  const tagLabels = { vegetarian: 'Vegetarian', vegan: 'Vegan' }
  const badgeLabels = {
    best_value: 'Best value',
    chefs_choice: 'Chef choice',
    healthy_pick: 'Healthy pick',
  }

  const allergenTags = (item.allergens || []).map((allergen) =>
    `<span class="dish-tag tag-allergen">${allergenLabels[allergen] || allergen}</span>`
  ).join('')
  const itemTags = (item.tags || []).map((tag) =>
    `<span class="dish-tag tag-${tag}">${tagLabels[tag] || tag}</span>`
  ).join('')
  const badgeTags = (item.badges || []).filter((badge) => badge !== 'popular_combo').map((badge) =>
    `<span class="dish-tag tag-badge">${badgeLabels[badge] || badge}</span>`
  ).join('')

  const calories = item.calories_estimate ? `~${item.calories_estimate} kcal` : ''
  const price = item.price_raw || formatCurrency(item.price)
  const ingredients = (item.ingredients_main || []).length
    ? `<div class="dish-desc">Ingredientes principais: ${escapeHTML(item.ingredients_main.join(', '))}</div>`
    : ''
  const portion = item.portion_size
    ? `<span class="dish-tag">${escapeHTML(item.portion_size)}</span>`
    : ''
  const spice = item.spice_level && item.spice_level !== 'unknown'
    ? `<span class="dish-tag">${escapeHTML(SPICE_LABELS[item.spice_level] || item.spice_level)}</span>`
    : ''
  const confidence = item.confidence != null
    ? `<span class="dish-tag">Confianca ${Math.round(Number(item.confidence) * 100)}%</span>`
    : ''

  return `<div class="dish-row">
    <div class="dish-info">
      <div class="dish-name">${escapeHTML(item.name || '')}</div>
      ${item.description ? `<div class="dish-desc">${escapeHTML(item.description)}</div>` : ''}
      ${ingredients}
      <div class="dish-meta">${allergenTags}${itemTags}${badgeTags}${portion}${spice}${confidence}</div>
    </div>
    <div class="dish-right">
      <div class="dish-price">${price || '-'}</div>
      ${calories ? `<div class="dish-cal">${calories}</div>` : ''}
    </div>
  </div>`
}

function renderAllergenMap(allergenCounts) {
  const allergens = {
    gluten: 'Gluten',
    lactose: 'Lactose',
    nuts: 'Nuts',
    shellfish: 'Shellfish',
    eggs: 'Eggs',
    soy: 'Soy',
  }
  const entries = Object.entries(allergens).filter(([key]) => allergenCounts[key] > 0)
  if (!entries.length) {
    return '<div class="empty-state">Nenhum alergeno identificado.</div>'
  }

  return `<div class="allergen-grid">${entries.map(([key, label]) => `
    <div class="allergen-card">
      <div class="allergen-name">${label}</div>
      <div class="allergen-count">${allergenCounts[key]}</div>
      <div class="history-meta">pratos</div>
    </div>
  `).join('')}</div>`
}

function renderRawAnalysis(text) {
  if (!text) {
    return '<div class="empty-state">Analise narrativa indisponivel.</div>'
  }
  return `<p class="raw-analysis-text">${escapeHTML(text)}</p>`
}

async function exportCurrentMenu() {
  if (!currentMenuId) {
    return
  }
  await exportMenu(currentMenuId)
}

async function exportMenu(menuId) {
  try {
    const response = await fetch(`/api/menus/${menuId}/export`, { method: 'POST' })
    const data = await response.json()
    if (!data.ok) {
      throw new Error(data.error || 'Falha ao exportar.')
    }
    window.open(data.url, '_blank')
    showToast('Export gerado com sucesso.', 'success')
  } catch (error) {
    showToast(error.message, 'error')
  }
}

async function loadHistory(query = '') {
  const historyList = document.getElementById('history-list')
  historyList.innerHTML = '<div class="empty-state">Carregando...</div>'
  try {
    const suffix = query ? `?q=${encodeURIComponent(query)}` : ''
    const response = await fetch(`/api/menus/history${suffix}`)
    const data = await response.json()
    renderHistoryList(data.menus || [])
  } catch {
    historyList.innerHTML = '<div class="empty-state">Erro ao carregar historico.</div>'
  }
}

function renderHistoryList(menus) {
  const historyList = document.getElementById('history-list')
  if (!menus.length) {
    historyList.innerHTML = '<div class="empty-state">Nenhum cardapio salvo ainda.</div>'
    return
  }

  historyList.innerHTML = menus.map((menu) => {
    const date = formatDate(menu.analyzed_at)
    const photoCount = `${menu.photo_count || 1} foto(s)`
    const classes = ['history-card']
    if (compareMode) {
      classes.push('compare-selecting')
    }
    if (compareMode && compareMenuA === menu.menu_id) {
      classes.push('compare-selected-a')
    }
    const clickHandler = compareMode ? `onclick="selectForCompare('${menu.menu_id}')"` : ''
    return `<div class="${classes.join(' ')}" ${clickHandler}>
      <div class="history-icon">${menu.cover_image ? `<img src="${menu.cover_image}" alt="Capa do cardapio" class="history-cover">` : 'AI'}</div>
      <div class="history-info">
        <div class="history-name">${escapeHTML(menu.restaurant_name || 'Sem nome')}</div>
        <div class="history-meta">${date} · ${photoCount}${menu.location_notes ? ' · ' + escapeHTML(menu.location_notes) : ''}</div>
        <div class="summary-chips">
          ${menu.price_range ? `<span class="chip">${escapeHTML(menu.price_range)}</span>` : ''}
          ${menu.total_items ? `<span class="chip">${menu.total_items} pratos</span>` : ''}
          ${menu.provider ? `<span class="badge-model-used">${escapeHTML((PROVIDER_META[menu.provider] || PROVIDER_META.claude).label)}</span>` : ''}
          ${(menu.cuisine_hints || []).map((cuisine) => `<span class="chip">${escapeHTML(cuisine)}</span>`).join('')}
        </div>
      </div>
      <div class="history-actions" onclick="event.stopPropagation()">
        <button class="ghost-btn small-btn" type="button" onclick="viewMenu('${menu.menu_id}')">Ver</button>
        <button class="ghost-btn small-btn" type="button" onclick="exportMenu('${menu.menu_id}')">Exportar</button>
        <button class="ghost-btn small-btn" type="button" onclick="startCompare('${menu.menu_id}')">Comparar</button>
        <button class="ghost-btn small-btn" type="button" onclick="deleteMenu('${menu.menu_id}')">Deletar</button>
      </div>
    </div>`
  }).join('')
}

async function viewMenu(menuId) {
  try {
    const response = await fetch(`/api/menus/${menuId}`)
    const data = await response.json()
    if (!data.ok) {
      throw new Error(data.error || 'Nao foi possivel abrir o cardapio.')
    }
    currentMenuId = data.menu_id
    switchTab('analyze')
    showResultsState(data)
  } catch (error) {
    showToast(error.message, 'error')
  }
}

async function deleteMenu(menuId) {
  const shouldDelete = window.confirm('Remover este cardapio do historico?')
  if (!shouldDelete) {
    return
  }

  try {
    const response = await fetch(`/api/menus/${menuId}`, { method: 'DELETE' })
    const data = await response.json()
    if (!data.ok) {
      throw new Error(data.error || 'Nao foi possivel remover o cardapio.')
    }
    showToast('Cardapio removido.', 'info')
    loadHistory(document.getElementById('history-search').value)
  } catch (error) {
    showToast(error.message, 'error')
  }
}

function startCompare(menuId) {
  compareMode = true
  compareMenuA = menuId
  document.getElementById('compare-banner').hidden = false
  document.getElementById('compare-banner-text').textContent = 'Cardapio A selecionado. Agora escolha o cardapio B.'
  document.getElementById('compare-view').hidden = true
  loadHistory(document.getElementById('history-search').value)
}

async function selectForCompare(menuId) {
  if (!compareMode) {
    return
  }
  if (menuId === compareMenuA) {
    showToast('Selecione um cardapio diferente.', 'error')
    return
  }

  compareMode = false
  document.getElementById('compare-banner').hidden = true

  try {
    const response = await fetch(`/api/menus/compare?a=${compareMenuA}&b=${menuId}`)
    const data = await response.json()
    if (!data.ok) {
      throw new Error(data.error || 'Falha na comparacao.')
    }
    renderCompareView(data)
  } catch (error) {
    showToast(error.message, 'error')
  }
}

function cancelCompare() {
  compareMode = false
  compareMenuA = null
  document.getElementById('compare-banner').hidden = true
  document.getElementById('compare-view').hidden = true
  document.getElementById('history-list').style.display = ''
  loadHistory(document.getElementById('history-search').value)
}

function closeCompareView() {
  document.getElementById('compare-view').hidden = true
  document.getElementById('history-list').style.display = ''
}

function renderCompareView(data) {
  const menuA = data.a
  const menuB = data.b
  const diff = data.diff || {}
  document.getElementById('history-list').style.display = 'none'

  const compareView = document.getElementById('compare-view')
  compareView.hidden = false
  document.getElementById('compare-grid').innerHTML = `
    ${renderCompareColumn(menuA)}
    <div class="compare-diff">
      ${renderDiffItem('Media', diff.price_avg_diff)}
      ${renderDiffItem('Itens', diff.items_diff)}
      ${renderDiffItem('Vegan', diff.vegan_diff)}
      ${renderDiffItem('Vegetarian', diff.vegetarian_diff)}
    </div>
    ${renderCompareColumn(menuB)}
  `
}

function renderCompareColumn(menu) {
  const summary = menu.summary || {}
  return `<div class="compare-col">
    <div class="compare-col-title">${escapeHTML(menu.restaurant_name || 'Sem nome')}</div>
    <div class="compare-stat"><span class="compare-stat-label">Faixa</span><span>${escapeHTML(summary.price_range_label || '-')}</span></div>
    <div class="compare-stat"><span class="compare-stat-label">Media</span><span>${formatCurrency(summary.price_avg)}</span></div>
    <div class="compare-stat"><span class="compare-stat-label">Minimo</span><span>${formatCurrency(summary.price_min)}</span></div>
    <div class="compare-stat"><span class="compare-stat-label">Maximo</span><span>${formatCurrency(summary.price_max)}</span></div>
    <div class="compare-stat"><span class="compare-stat-label">Pratos</span><span>${summary.total_items || 0}</span></div>
    <div class="compare-stat"><span class="compare-stat-label">Vegan</span><span>${(summary.dietary_counts || {}).vegan || 0}</span></div>
    <div class="compare-stat"><span class="compare-stat-label">Vegetarian</span><span>${(summary.dietary_counts || {}).vegetarian || 0}</span></div>
    <div class="history-actions" style="margin-top:12px">
      <button class="ghost-btn small-btn" type="button" onclick="viewMenu('${menu.menu_id}')">Abrir</button>
      <button class="ghost-btn small-btn" type="button" onclick="exportMenu('${menu.menu_id}')">Exportar</button>
    </div>
  </div>`
}

function renderDiffItem(label, value) {
  const number = Number(value || 0)
  const signal = number > 0 ? `+${number}` : `${number}`
  const cssClass = number > 0 ? 'diff-positive' : number < 0 ? 'diff-negative' : 'diff-neutral'
  return `<div class="diff-item">
    <div class="diff-label">${label}</div>
    <div class="diff-val ${cssClass}">${signal}</div>
  </div>`
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container')
  const toast = document.createElement('div')
  toast.className = `toast toast-${type}`
  toast.textContent = message
  container.appendChild(toast)
  setTimeout(() => {
    toast.style.opacity = '0'
    toast.style.transition = 'opacity 0.3s ease'
    setTimeout(() => toast.remove(), 300)
  }, 3200)
}

function escapeHTML(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function formatCurrency(value) {
  if (value == null || Number.isNaN(Number(value))) {
    return '-'
  }
  return `R$ ${Number(value).toFixed(2).replace('.', ',')}`
}

function formatDate(isoString) {
  if (!isoString) {
    return ''
  }
  try {
    const date = new Date(isoString)
    return date.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })
  } catch {
    return isoString.slice(0, 10)
  }
}