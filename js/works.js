const worksGrid = document.getElementById("worksGrid")
const filterBar = document.getElementById("filterBar")
const modal = document.getElementById("worksModal")
const modalCloseBtn = document.querySelector(".modal-close")
const modalLeftPanel = document.getElementById("modal-left")
const modalRightPanel = document.querySelector(".modal-right")
const modalMedia = document.getElementById("modal-media")

const mdFiles = ["./works-data/Ophelia.md", "./works-data/Ophanim.md"]
const sessionWatermarkSeed = `SW-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,6).toUpperCase()}`

let works = []
let filterGroups = []
let activeFilters = {}
let filterPanelOpen = false
let activeCard = null
let activeMediaElement = null
let openTl = null
let closeTl = null

function normalizeFilterValue(value){
  if(value == null) return ""
  const normalized = String(value).trim().toLowerCase().replace(/\s+/g, "-")
  if(normalized === "quantum-refreaction" || normalized === "quantum-refractio") return "quantum-refraction"
  return normalized
}

function getWorkFieldValue(work, key){
  const value = work?.[key]
  if(value == null) return ""
  return normalizeFilterValue(value)
}

function getWorkContent(work){
  if(work?.content && typeof work.content === "object"){
    return {
      kind: normalizeFilterValue(work.content.kind || "image"),
      src: work.content.src || work.image || "",
      poster: work.content.poster || work.thumbnail || "",
      link: work.content.link || "",
      modelFormat: normalizeFilterValue(work.content.modelFormat || ""),
      sources: Array.isArray(work.content.sources) ? work.content.sources : []
    }
  }

  return {
    kind: "image",
    src: work?.image || "",
    poster: work?.thumbnail || "",
    link: "",
    modelFormat: "",
    sources: []
  }
}

function setupImageProtection(){
  document.addEventListener("contextmenu",(event)=>{
    if(event.target instanceof HTMLImageElement || event.target instanceof HTMLVideoElement){
      event.preventDefault()
    }
  })

  document.addEventListener("dragstart",(event)=>{
    if(event.target instanceof HTMLImageElement){
      event.preventDefault()
    }
  })
}

function buildWatermarkDataUri(text){
  const safeText = String(text).replace(/[<>&"]/g, "")
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="380" height="260"><g transform="rotate(-28 190 130)"><text x="20" y="95" font-size="18" fill="rgba(255,255,255,0.20)" font-family="Arial, sans-serif">${safeText}</text><text x="20" y="165" font-size="18" fill="rgba(255,255,255,0.17)" font-family="Arial, sans-serif">${safeText}</text></g></svg>`
  return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}")`
}

function applyWatermarkLayer(layer, watermarkText){
  if(!layer) return
  layer.style.setProperty("--watermark-image", buildWatermarkDataUri(watermarkText))
}

function ensureModalWatermarkLayer(){
  let layer = document.getElementById("modal-watermark")
  if(layer) return layer
  layer = document.createElement("div")
  layer.id = "modal-watermark"
  layer.className = "watermark-layer modal-watermark"
  layer.setAttribute("aria-hidden", "true")
  modalRightPanel?.appendChild(layer)
  return layer
}

async function loadFilterConfig(){
  try{
    const res = await fetch("./works-data/filters.json")
    if(!res.ok) throw new Error(`Failed to load filters.json: ${res.status}`)
    const data = await res.json()
    const groups = Array.isArray(data?.groups) ? data.groups : []
    filterGroups = groups
      .filter((g)=>g && g.key && Array.isArray(g.options))
      .map((g)=>({
        key: String(g.key),
        label: String(g.label || g.key),
        options: g.options.map((o)=>String(o))
      }))
  }catch(err){
    console.warn(err)
    filterGroups = [
      {key: "type", label: "Type", options: ["painting", "mixed-media", "sculpture", "video", "audio", "model"]},
      {key: "series", label: "Series", options: ["female divinity", "quantum refraction"]}
    ]
  }

  activeFilters = {}
  filterGroups.forEach((group)=>{ activeFilters[group.key] = "all" })
  renderFilterBar()
}

function renderFilterBar(){
  if(!filterBar) return
  const renderGroupOptions = (group)=>{
    const allBtn = `<button class="filter-option-btn active" data-group="${group.key}" data-value="all">All ${group.label}</button>`
    const optionBtns = group.options
      .map((option)=>`<button class="filter-option-btn" data-group="${group.key}" data-value="${normalizeFilterValue(option)}">${option}</button>`)
      .join("")
    return `
      <div class="filter-group" data-group="${group.key}">
        <div class="filter-group-title">${group.label}</div>
        <div class="filter-options">${allBtn}${optionBtns}</div>
      </div>
    `
  }

  filterBar.innerHTML = `
    <div class="filter-control ${filterPanelOpen ? "open" : ""}">
      <button class="filter-trigger-btn" type="button" aria-expanded="${filterPanelOpen}">
        <strong class="btn-label">Filter${getActiveFilterCount() > 0 ? ` (${getActiveFilterCount()})` : ""}</strong>
        <span id="container-stars" aria-hidden="true"><span id="stars"></span></span>
        <span id="glow" aria-hidden="true"><span class="circle"></span><span class="circle"></span></span>
      </button>
      <div class="filter-panel ${filterPanelOpen ? "active" : ""}">
        ${filterGroups.map(renderGroupOptions).join("")}
      </div>
    </div>
  `
}

function getActiveFilterCount(){
  return Object.values(activeFilters).filter((v)=>v && v !== "all").length
}

function syncFilterUI(){
  filterBar.querySelectorAll(".filter-option-btn").forEach((btn)=>{
    const groupKey = btn.getAttribute("data-group")
    const value = btn.getAttribute("data-value") || "all"
    const isActive = activeFilters[groupKey || ""] === value
    btn.classList.toggle("active", isActive)
  })

  const triggerLabel = filterBar.querySelector(".filter-trigger-btn .btn-label")
  if(triggerLabel){
    const activeCount = getActiveFilterCount()
    triggerLabel.textContent = activeCount > 0 ? `Filter (${activeCount})` : "Filter"
  }
}

function setupFilterEvents(){
  filterBar?.addEventListener("click",(event)=>{
    const target = event.target instanceof HTMLElement ? event.target : null
    if(!target) return

    const trigger = target.closest(".filter-trigger-btn")
    if(trigger){
      filterPanelOpen = !filterPanelOpen
      const panel = filterBar.querySelector(".filter-panel")
      const control = filterBar.querySelector(".filter-control")
      panel?.classList.toggle("active", filterPanelOpen)
      control?.classList.toggle("open", filterPanelOpen)
      trigger.setAttribute("aria-expanded", String(filterPanelOpen))
      return
    }

    const optionBtn = target.closest(".filter-option-btn")
    if(!optionBtn) return
    const groupKey = optionBtn.getAttribute("data-group")
    const value = optionBtn.getAttribute("data-value") || "all"
    if(!groupKey) return

    activeFilters[groupKey] = value
    syncFilterUI()
    applyFilters()
  })

  document.addEventListener("click",(event)=>{
    if(!filterPanelOpen || !filterBar) return
    const target = event.target instanceof Node ? event.target : null
    if(target && !filterBar.contains(target)){
      filterPanelOpen = false
      const panel = filterBar.querySelector(".filter-panel")
      const control = filterBar.querySelector(".filter-control")
      const trigger = filterBar.querySelector(".filter-trigger-btn")
      panel?.classList.remove("active")
      control?.classList.remove("open")
      trigger?.setAttribute("aria-expanded", "false")
    }
  })
}

async function loadWorks(){
  try{
    const res = await fetch("./works-data/works.json")
    if(!res.ok) throw new Error(`Failed to load works.json: ${res.status}`)
    const data = await res.json()
    works = Array.isArray(data) ? data : []
    applyFilters()
    return
  }catch(err){
    console.error(err)
  }

  works = []
  for(const file of mdFiles){
    try{
      const res = await fetch(file)
      if(!res.ok) throw new Error(`Failed to load works data: ${file} (${res.status})`)
      const text = await res.text()
      const parts = text.split("---")
      if(parts.length < 3) continue
      const metaRaw = parts[1]
      const content = parts.slice(2).join("---")
      const meta = {}
      metaRaw.split("\n").forEach((line)=>{
        const [key,value] = line.split(":")
        if(key && value) meta[key.trim()] = value.trim()
      })
      meta.description = content.trim()
      works.push(meta)
    }catch(err){
      console.error(err)
    }
  }
  applyFilters()
}

function applyFilters(){
  const filtered = works.filter((work)=>{
    return filterGroups.every((group)=>{
      const selected = activeFilters[group.key] || "all"
      if(selected === "all") return true
      return getWorkFieldValue(work, group.key) === selected
    })
  })
  renderWorks(filtered)
}

function renderWorks(list){
  worksGrid.innerHTML = ""
  if(!Array.isArray(list) || list.length === 0){
    worksGrid.innerHTML = `<p style="color:#fff;opacity:.8;">暂无作品数据（请检查控制台的加载错误）</p>`
    return
  }

  list.forEach((work)=>{
    const content = getWorkContent(work)
    const preview = work.thumbnail || content.poster || content.src || ""
    const card = document.createElement("div")
    card.className = "work-card"
    card.innerHTML = `
      <img src="${preview}" alt="${work.title || "work"}">
      <div class="watermark-layer card-watermark" aria-hidden="true"></div>
      <div class="work-meta"><strong>${work.title || "Untitled"}</strong> · ${work.year || ""}</div>
    `
    applyWatermarkLayer(card.querySelector(".card-watermark"), `${work.title || "Untitled"} · Si Wu · ${sessionWatermarkSeed}`)
    card.addEventListener("click",()=>openAnimation(work, card))
    worksGrid.appendChild(card)
  })
}

function setMetaText(id, value, prefix = ""){
  const el = document.getElementById(id)
  if(!el) return
  el.textContent = value ? `${prefix}${value}` : ""
}

function setModalMedia(work){
  modalMedia.innerHTML = ""
  const content = getWorkContent(work)
  const kind = content.kind || "image"
  let mediaEl = null

  if(kind === "video"){
    mediaEl = document.createElement("video")
    mediaEl.className = "modal-main-media"
    mediaEl.controls = true
    mediaEl.playsInline = true
    mediaEl.preload = "metadata"
    mediaEl.setAttribute("controlsList", "nodownload noplaybackrate")
    if(content.poster) mediaEl.poster = content.poster
    if(content.sources.length > 0){
      content.sources.forEach((srcObj)=>{
        const src = document.createElement("source")
        src.src = srcObj.src || ""
        if(srcObj.type) src.type = srcObj.type
        mediaEl.appendChild(src)
      })
    }else{
      mediaEl.src = content.src || work.image || ""
    }
  }else if(kind === "audio"){
    mediaEl = document.createElement("audio")
    mediaEl.className = "modal-main-media modal-audio"
    mediaEl.controls = true
    mediaEl.preload = "metadata"
    mediaEl.setAttribute("controlsList", "nodownload noplaybackrate")
    mediaEl.src = content.src || ""
  }else if(kind === "web"){
    if(content.link){
      mediaEl = document.createElement("iframe")
      mediaEl.className = "modal-main-media modal-iframe"
      mediaEl.src = content.link
      mediaEl.referrerPolicy = "strict-origin-when-cross-origin"
      mediaEl.allowFullscreen = true
    }
  }else if(kind === "model"){
    // 简化实现：优先外链预览，避免强绑 특정 3D 运行时
    if(content.link){
      mediaEl = document.createElement("iframe")
      mediaEl.className = "modal-main-media modal-iframe"
      mediaEl.src = content.link
      mediaEl.allowFullscreen = true
    }
  }

  if(!mediaEl){
    mediaEl = document.createElement("img")
    mediaEl.className = "modal-main-media"
    mediaEl.src = content.src || work.image || ""
    mediaEl.alt = work.title || "work image"
  }

  modalMedia.appendChild(mediaEl)
  activeMediaElement = mediaEl

  const modalWatermark = ensureModalWatermarkLayer()
  applyWatermarkLayer(modalWatermark, `${work.title || "Untitled"} · Si Wu Studio · ${sessionWatermarkSeed}`)
}

function setModalContent(work){
  document.getElementById("modal-title").textContent = work.title || "Untitled"
  setMetaText("modal-year", work.year)
  setMetaText("modal-type", work.type)
  setMetaText("modal-medium", work.medium)
  setMetaText("modal-size", work.size)
  setMetaText("modal-desc", work.description)
  setModalMedia(work)
}

function openAnimation(work, card){
  const cardImage = card?.querySelector("img")
  if(!cardImage) return
  if(openTl){ openTl.kill(); openTl = null }
  if(closeTl){ closeTl.kill(); closeTl = null }

  activeCard = card
  setModalContent(work)
  modal.classList.add("active")
  gsap.set([modalLeftPanel, modalCloseBtn], {autoAlpha: 0, y: 18})
  gsap.set(modal, {backgroundColor: "rgba(0,0,0,0)"})

  const canFlip = activeMediaElement instanceof HTMLImageElement
  if(!canFlip){
    openTl = gsap.timeline({defaults:{ease:"power3.out"}})
    openTl.to(modal, {backgroundColor:"rgba(0,0,0,0.9)", duration:0.3})
      .fromTo(modalRightPanel, {autoAlpha:0, y:20}, {autoAlpha:1, y:0, duration:0.32}, 0.08)
      .to([modalLeftPanel, modalCloseBtn], {autoAlpha:1, y:0, duration:0.28, stagger:0.03}, 0.18)
    return
  }

  const modalImg = activeMediaElement
  gsap.set(modalImg, {autoAlpha: 0, clearProps: "all"})
  const fromRect = cardImage.getBoundingClientRect()
  const toRect = modalImg.getBoundingClientRect()
  gsap.set(modalImg, {
    position:"fixed",
    top:fromRect.top,
    left:fromRect.left,
    width:fromRect.width,
    height:fromRect.height,
    autoAlpha: 1,
    margin: 0,
    borderRadius: 8,
    zIndex: 1001
  })

  openTl = gsap.timeline({defaults:{ease:"power3.out"}})
  openTl.to(modal, {backgroundColor:"rgba(0,0,0,0.9)", duration:0.35})
    .to(modalImg, {
      top:toRect.top,
      left:toRect.left,
      width:toRect.width,
      height:toRect.height,
      borderRadius: 4,
      duration:0.55
    }, 0)
    .to([modalLeftPanel, modalCloseBtn], {autoAlpha:1, y:0, duration:0.32, stagger:0.04}, 0.24)
    .add(()=> gsap.set(modalImg, {clearProps:"position,top,left,width,height,margin,zIndex,borderRadius"}))
}

function closeAnimation(){
  if(closeTl){ closeTl.kill(); closeTl = null }
  if(openTl){ openTl.kill(); openTl = null }
  const canFlipBack = activeMediaElement instanceof HTMLImageElement

  if(!canFlipBack){
    closeTl = gsap.timeline({defaults:{ease:"power2.inOut"}})
    closeTl.to([modalLeftPanel, modalCloseBtn, modalRightPanel], {autoAlpha:0, y:12, duration:0.2})
      .to(modal, {
        backgroundColor:"rgba(0,0,0,0)",
        duration:0.25,
        onComplete:()=>{
          modal.classList.remove("active")
          gsap.set([modal, modalLeftPanel, modalCloseBtn, modalRightPanel], {clearProps:"all"})
          activeCard = null
          activeMediaElement = null
        }
      }, 0.02)
    return
  }

  const modalImg = activeMediaElement
  const targetImg = activeCard?.querySelector("img")
  const toRect = targetImg?.getBoundingClientRect()
  const fromRect = modalImg.getBoundingClientRect()
  gsap.set(modalImg, {
    position:"fixed",
    top:fromRect.top,
    left:fromRect.left,
    width:fromRect.width,
    height:fromRect.height,
    margin:0,
    zIndex:1001
  })

  closeTl = gsap.timeline({defaults:{ease:"power2.inOut"}})
  closeTl.to([modalLeftPanel, modalCloseBtn], {autoAlpha:0, y:16, duration:0.22})
    .to(modal, {backgroundColor:"rgba(0,0,0,0)", duration:0.3}, 0.06)
    .to(modalImg, {
      top: toRect ? toRect.top : fromRect.top + 20,
      left: toRect ? toRect.left : fromRect.left,
      width: toRect ? toRect.width : fromRect.width * 0.94,
      height: toRect ? toRect.height : fromRect.height * 0.94,
      autoAlpha: toRect ? 1 : 0,
      duration:0.4,
      onComplete:()=>{
        modal.classList.remove("active")
        gsap.set([modal, modalImg, modalLeftPanel, modalCloseBtn], {clearProps:"all"})
        activeCard = null
        activeMediaElement = null
      }
    }, 0.02)
}

modalCloseBtn.addEventListener("click", closeAnimation)
modal.addEventListener("click",(event)=>{ if(event.target === modal) closeAnimation() })
document.addEventListener("keydown",(event)=>{ if(event.key === "Escape" && modal.classList.contains("active")) closeAnimation() })

setupFilterEvents()
setupImageProtection()
loadFilterConfig().then(loadWorks)