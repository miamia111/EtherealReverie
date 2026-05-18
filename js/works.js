const worksGrid = document.getElementById("worksGrid")
const filterBar = document.getElementById("filterBar")
const modal = document.getElementById("worksModal")
const modalCloseBtn = document.querySelector(".modal-close")
const modalLeftPanel = document.getElementById("modal-left")
const modalRightPanel = document.querySelector(".modal-right")
const modalMedia = document.getElementById("modal-media")
const modalThumbnails = document.getElementById("modal-thumbnails")
const modalNavPrev = document.querySelector(".modal-nav-prev")
const modalNavNext = document.querySelector(".modal-nav-next")
const searchInput = document.getElementById("works-search")
const mdFiles = ["./works-data/Ophelia.md", "./works-data/Ophanim.md"]

let works = []
let filterGroups = []
let activeFilters = {}
let filterPanelOpen = false
let activeCard = null
let activeMediaElement = null
let activeWork = null
let activeMediaList = []
let activeMediaIndex = 0
let openTl = null
let closeTl = null
const initialWorkId = new URLSearchParams(window.location.search).get("id")
let hasTriedOpenFromUrl = false

function normalizeFilterValue(value) {
  if (value == null) return ""
  const normalized = String(value).trim().toLowerCase().replace(/\s+/g, "-")
  if (normalized === "quantum-refreaction" || normalized === "quantum-refractio") return "quantum-refraction"
  return normalized
}

function normalizeMediaItem(raw) {
  if (!raw || typeof raw !== "object") {
    return { kind: "image", src: "", poster: "", link: "", modelFormat: "", sources: [] }
  }
  return {
    kind: normalizeFilterValue(raw.kind || "image"),
    src: raw.src || "",
    poster: raw.poster || "",
    link: raw.link || "",
    modelFormat: normalizeFilterValue(raw.modelFormat || ""),
    sources: Array.isArray(raw.sources) ? raw.sources : [],
  }
}

function getWorkMediaList(work) {
  if (Array.isArray(work?.media) && work.media.length > 0) {
    return work.media.map(normalizeMediaItem).filter((item) => item.src || item.link)
  }
  if (work?.content && typeof work.content === "object") {
    return [normalizeMediaItem({
      kind: work.content.kind || "image",
      src: work.content.src || work.image || "",
      poster: work.content.poster || work.thumbnail || "",
      link: work.content.link || "",
      modelFormat: work.content.modelFormat || "",
      sources: work.content.sources,
    })]
  }
  const fallbackSrc = work?.image || ""
  if (!fallbackSrc) return []
  return [normalizeMediaItem({
    kind: "image",
    src: fallbackSrc,
    poster: work?.thumbnail || fallbackSrc,
    link: "",
    modelFormat: "",
    sources: [],
  })]
}

function getWorkContent(work) {
  const list = getWorkMediaList(work)
  if (list.length > 0) return list[0]
  return {
    kind: "image",
    src: work?.image || "",
    poster: work?.thumbnail || "",
    link: "",
    modelFormat: "",
    sources: [],
  }
}

function getWorkPreviewSrc(work) {
  const first = getWorkContent(work)
  return work?.thumbnail || first.poster || first.src || work?.image || ""
}

function getMediaThumbSrc(item) {
  if (item.poster) return item.poster
  if (item.kind === "image") return item.src
  if (item.kind === "video" && item.src && /\.(jpg|jpeg|png|webp|gif)(\?|$)/i.test(item.src)) return item.src
  return ""
}

function getMediaTypeIcon(kind) {
  const icons = {
    image: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5h14v14H5V5zm2 10.5 2.5-3 2 2.5 3-4L17 16H7v-.5z"/></svg>',
    video: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7L8 5z"/></svg>',
    audio: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6z"/></svg>',
    model: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2 2 7l10 5 10-5-10-5zm0 8.5L4 6.5v5L12 17l8-5.5v-5l-8 4zM4 14.5 12 19l8-4.5v5L12 24 4 19.5v-5z"/></svg>',
    web: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 17.93A8 8 0 0 1 4.07 13H11v6.93zM13 4.07V11h6.93A8 8 0 0 0 13 4.07z"/></svg>',
  }
  return icons[kind] || icons.image
}

function convertToEmbedUrl(url) {
  if (!url) return ""
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/
  const match = url.match(regExp)
  if (match && match[2].length === 11) {
    return `https://www.youtube.com/embed/${match[2]}?rel=0&showinfo=0&enablejsapi=1`
  }
  if (url.includes("vimeo.com/")) {
    const id = url.split("/").pop()
    return `https://player.vimeo.com/video/${id}`
  }
  return url
}

function setupImageProtection() {
  document.addEventListener("contextmenu", (event) => {
    if (event.target instanceof HTMLImageElement || event.target instanceof HTMLVideoElement) {
      event.preventDefault()
    }
  })

  document.addEventListener("dragstart", (event) => {
    if (event.target instanceof HTMLImageElement) {
      event.preventDefault()
    }
  })
}

async function loadFilterConfig() {
  try {
    const res = await fetch("./works-data/filters.json")
    if (!res.ok) throw new Error(`Failed to load filters.json: ${res.status}`)
    const data = await res.json()
    const groups = Array.isArray(data?.groups) ? data.groups : []
    filterGroups = groups
      .filter((g) => g && g.key && Array.isArray(g.options))
      .map((g) => ({
        key: String(g.key),
        label: String(g.label || g.key),
        options: g.options.map((o) => String(o)),
      }))
  } catch (err) {
    console.warn(err)
    filterGroups = [
      { key: "type", label: "Type", options: ["painting", "mixed-media", "sculpture", "video", "audio", "model"] },
      { key: "series", label: "Series", options: ["female divinity", "quantum refraction"] },
    ]
  }

  activeFilters = {}
  filterGroups.forEach((group) => {
    activeFilters[group.key] = "all"
  })
  renderFilterBar()
}

function renderFilterBar() {
  if (!filterBar) return
  const renderGroupOptions = (group) => {
    const allBtn = `<button class="filter-option-btn active" data-group="${group.key}" data-value="all">All ${group.label}</button>`
    const optionBtns = group.options
      .map((option) => `<button class="filter-option-btn" data-group="${group.key}" data-value="${normalizeFilterValue(option)}">${option}</button>`)
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

function getActiveFilterCount() {
  return Object.values(activeFilters).filter((v) => v && v !== "all").length
}

function syncFilterUI() {
  filterBar.querySelectorAll(".filter-option-btn").forEach((btn) => {
    const groupKey = btn.getAttribute("data-group")
    const value = btn.getAttribute("data-value") || "all"
    const isActive = activeFilters[groupKey || ""] === value
    btn.classList.toggle("active", isActive)
  })

  const triggerLabel = filterBar.querySelector(".filter-trigger-btn .btn-label")
  if (triggerLabel) {
    const activeCount = getActiveFilterCount()
    triggerLabel.textContent = activeCount > 0 ? `Filter (${activeCount})` : "Filter"
  }
}

function setupSearchEvents() {
  if (!searchInput) return

  searchInput.addEventListener("input", () => {
    const value = searchInput.value.trim()
    if (value !== "") {
      filterGroups.forEach((group) => {
        activeFilters[group.key] = "all"
      })
      syncFilterUI()
    }
    applyFilters()
  })
}

function setupFilterEvents() {
  filterBar?.addEventListener("click", (event) => {
    const target = event.target instanceof HTMLElement ? event.target : null
    if (!target) return

    const trigger = target.closest(".filter-trigger-btn")
    if (trigger) {
      filterPanelOpen = !filterPanelOpen
      const panel = filterBar.querySelector(".filter-panel")
      const control = filterBar.querySelector(".filter-control")
      panel?.classList.toggle("active", filterPanelOpen)
      control?.classList.toggle("open", filterPanelOpen)
      trigger.setAttribute("aria-expanded", String(filterPanelOpen))
      return
    }

    const optionBtn = target.closest(".filter-option-btn")
    if (!optionBtn) return
    if (searchInput) {
      searchInput.value = ""
    }
    const groupKey = optionBtn.getAttribute("data-group")
    const value = optionBtn.getAttribute("data-value") || "all"
    if (!groupKey) return

    activeFilters[groupKey] = value
    syncFilterUI()
    applyFilters()
  })

  document.addEventListener("click", (event) => {
    if (!filterPanelOpen || !filterBar) return
    const target = event.target instanceof Node ? event.target : null
    if (target && !filterBar.contains(target)) {
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

async function loadWorks() {
  try {
    const res = await fetch("./works-data/works.json")
    if (!res.ok) throw new Error(`Failed to load works.json: ${res.status}`)
    const data = await res.json()
    works = Array.isArray(data) ? data : []
    applyFilters()
    return
  } catch (err) {
    console.error(err)
  }

  works = []
  for (const file of mdFiles) {
    try {
      const res = await fetch(file)
      if (!res.ok) throw new Error(`Failed to load works data: ${file} (${res.status})`)
      const text = await res.text()
      const parts = text.split("---")
      if (parts.length < 3) continue
      const metaRaw = parts[1]
      const content = parts.slice(2).join("---")
      const meta = {}
      metaRaw.split("\n").forEach((line) => {
        const [key, value] = line.split(":")
        if (key && value) meta[key.trim()] = value.trim()
      })
      meta.description = content.trim()
      works.push(meta)
    } catch (err) {
      console.error(err)
    }
  }
  applyFilters()
}

function applyFilters() {
  const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : ""

  const filtered = works.filter((work) => {
    const matchesFilters = filterGroups.every((group) => {
      const selected = activeFilters[group.key] || "all"
      if (selected === "all") return true
      return getWorkFieldValue(work, group.key) === selected
    })

    const title = (work.title || "").toLowerCase()
    const desc = (work.description || "").toLowerCase()
    const matchesSearch = title.includes(searchTerm) || desc.includes(searchTerm)

    return matchesFilters && matchesSearch
  })

  renderWorks(filtered)
}

function getWorkFieldValue(work, key) {
  const value = work?.[key]
  if (value == null) return ""
  return normalizeFilterValue(value)
}

function renderWorks(list) {
  worksGrid.innerHTML = ""
  if (!Array.isArray(list) || list.length === 0) {
    worksGrid.innerHTML = `<p style="color:#fff;opacity:.8;">暂无作品数据（请检查控制台的加载错误）</p>`
    return
  }

  list.forEach((work) => {
    const preview = getWorkPreviewSrc(work)
    const mediaCount = getWorkMediaList(work).length
    const countBadge = mediaCount > 1 ? `<span class="work-media-count" aria-label="${mediaCount} 个媒体">${mediaCount}</span>` : ""
    const card = document.createElement("div")
    card.className = "work-card"
    card.innerHTML = `
      <img src="${preview}" alt="${work.title || "work"}">
      ${countBadge}
      <div class="work-meta"><strong>${work.title || "Untitled"}</strong> · ${work.year || ""}</div>
    `
    card.addEventListener("click", () => openAnimation(work, card))
    worksGrid.appendChild(card)
  })

  tryOpenWorkFromUrl(list)
}

function tryOpenWorkFromUrl(list) {
  if (hasTriedOpenFromUrl || !initialWorkId || !Array.isArray(list) || list.length === 0) {
    return
  }

  const targetIndex = list.findIndex((work) => String(work?.id) === String(initialWorkId))
  if (targetIndex === -1) {
    return
  }

  hasTriedOpenFromUrl = true
  const targetCard = worksGrid.children[targetIndex]
  if (targetCard instanceof HTMLElement) {
    requestAnimationFrame(() => {
      openAnimation(list[targetIndex], targetCard)
      clearWorkIdFromUrl()
    })
  }
}

function clearWorkIdFromUrl() {
  const url = new URL(window.location.href)
  if (!url.searchParams.has("id")) return
  url.searchParams.delete("id")
  const nextSearch = url.searchParams.toString()
  const nextUrl = `${url.pathname}${nextSearch ? `?${nextSearch}` : ""}${url.hash}`
  window.history.replaceState({}, "", nextUrl)
}

function setMetaText(id, value, prefix = "") {
  const el = document.getElementById(id)
  if (!el) return
  el.textContent = value ? `${prefix}${value}` : ""
}

function stopActiveMedia() {
  if (!modalMedia) return
  modalMedia.querySelectorAll("video, audio").forEach((el) => {
    try {
      el.pause()
    } catch (_) {}
  })
  modalMedia.querySelectorAll("iframe").forEach((frame) => {
    frame.src = "about:blank"
  })
}

function createMediaElement(content, work) {
  let kind = content.kind || "image"
  let mediaEl = null
  const rawUrl = content.link || content.src || ""

  if (kind === "web" && (rawUrl.includes("youtube.com") || rawUrl.includes("youtu.be") || rawUrl.includes("vimeo.com"))) {
    kind = "video"
  }

  if (kind === "video") {
    const isExternal =
      content.link ||
      (content.src && content.src.includes("http") && !content.src.match(/\.(mp4|webm|ogg|mov|m4v)(\?|$)/i))

    if (isExternal) {
      mediaEl = document.createElement("iframe")
      mediaEl.className = "modal-main-media modal-iframe video-external"
      const finalUrl = convertToEmbedUrl(content.link || content.src)
      mediaEl.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      mediaEl.allowFullscreen = true
      setTimeout(() => {
        if (finalUrl) mediaEl.src = finalUrl
      }, 0)
    } else {
      mediaEl = document.createElement("video")
      mediaEl.className = "modal-main-media"
      mediaEl.controls = true
      mediaEl.playsInline = true
      mediaEl.preload = "metadata"
      mediaEl.setAttribute("controlsList", "nodownload noplaybackrate")
      if (content.poster) mediaEl.poster = content.poster
      if (content.sources && content.sources.length > 0) {
        content.sources.forEach((srcObj) => {
          const src = document.createElement("source")
          src.src = srcObj.src || ""
          if (srcObj.type) src.type = srcObj.type
          mediaEl.appendChild(src)
        })
      } else {
        mediaEl.src = content.src || work?.image || ""
      }
    }
  } else if (kind === "audio") {
    mediaEl = document.createElement("audio")
    mediaEl.className = "modal-main-media modal-audio"
    mediaEl.controls = true
    mediaEl.src = content.src || ""
  } else if (kind === "web" || kind === "model") {
    if (content.link) {
      const wrapper = document.createElement("div")
      wrapper.className = "modal-embed-wrap"
      wrapper.style.position = "relative"
      wrapper.style.width = "100%"
      wrapper.style.height = "100%"
      wrapper.innerHTML = `<div class="media-loader-container"><div class="loader">Loading...</div></div>`

      mediaEl = document.createElement("iframe")
      mediaEl.className = `modal-main-media modal-iframe modal-${kind}`
      mediaEl.referrerPolicy = "strict-origin-when-cross-origin"
      mediaEl.allowFullscreen = true
      if (kind === "model") {
        mediaEl.src = convertToEmbedUrl(content.link)
        mediaEl.allow = "autoplay; fullscreen; xr-spatial-tracking"
        mediaEl.setAttribute("xr-spatial-tracking", "")
        mediaEl.setAttribute("execution-while-out-of-viewport", "")
        mediaEl.setAttribute("execution-while-not-rendered", "")
        mediaEl.frameBorder = "0"
      } else {
        mediaEl.src = content.link
      }
      mediaEl.onload = function () {
        const loaderContainer = wrapper.querySelector(".media-loader-container")
        if (loaderContainer) {
          loaderContainer.style.opacity = "0"
          setTimeout(() => loaderContainer.remove(), 500)
        }
      }
      wrapper.appendChild(mediaEl)
      return wrapper
    }
  }

  if (!mediaEl) {
    mediaEl = document.createElement("img")
    mediaEl.className = "modal-main-media"
    mediaEl.src = content.src || work?.image || ""
    mediaEl.alt = work?.title || "work image"
  }

  return mediaEl
}

function updateModalNavState() {
  const count = activeMediaList.length
  const hideNav = count <= 1
  if (modalNavPrev) {
    modalNavPrev.disabled = hideNav || activeMediaIndex <= 0
    modalNavPrev.style.visibility = hideNav ? "hidden" : "visible"
  }
  if (modalNavNext) {
    modalNavNext.disabled = hideNav || activeMediaIndex >= count - 1
    modalNavNext.style.visibility = hideNav ? "hidden" : "visible"
  }
  if (modalThumbnails) {
    modalThumbnails.style.display = hideNav ? "none" : "flex"
  }
}

function syncThumbnailActiveState() {
  if (!modalThumbnails) return
  modalThumbnails.querySelectorAll(".modal-thumb").forEach((btn, index) => {
    const isActive = index === activeMediaIndex
    btn.classList.toggle("active", isActive)
    btn.setAttribute("aria-selected", isActive ? "true" : "false")
  })
}

function renderModalThumbnails() {
  if (!modalThumbnails) return
  modalThumbnails.innerHTML = ""

  activeMediaList.forEach((item, index) => {
    const btn = document.createElement("button")
    btn.type = "button"
    btn.className = `modal-thumb${index === activeMediaIndex ? " active" : ""}`
    btn.setAttribute("role", "tab")
    btn.setAttribute("aria-selected", index === activeMediaIndex ? "true" : "false")
    btn.setAttribute("aria-label", `媒体 ${index + 1}：${item.kind}`)

    const thumbSrc = getMediaThumbSrc(item)
    if (thumbSrc) {
      const img = document.createElement("img")
      img.src = thumbSrc
      img.alt = ""
      img.loading = "lazy"
      btn.appendChild(img)
    } else {
      const placeholder = document.createElement("span")
      placeholder.className = "modal-thumb-placeholder"
      placeholder.textContent = item.kind
      btn.appendChild(placeholder)
    }

    const badge = document.createElement("span")
    badge.className = "media-type-badge"
    badge.innerHTML = getMediaTypeIcon(item.kind)
    btn.appendChild(badge)

    btn.addEventListener("click", () => showModalMedia(index))
    modalThumbnails.appendChild(btn)
  })
}

function showModalMedia(index) {
  if (!activeWork || index < 0 || index >= activeMediaList.length) return
  stopActiveMedia()
  activeMediaIndex = index
  modalMedia.innerHTML = ""

  const content = activeMediaList[index]
  const mediaEl = createMediaElement(content, activeWork)
  modalMedia.appendChild(mediaEl)
  activeMediaElement = mediaEl instanceof HTMLElement && mediaEl.classList.contains("modal-embed-wrap")
    ? mediaEl.querySelector(".modal-main-media") || mediaEl
    : mediaEl

  updateModalNavState()
  syncThumbnailActiveState()
}

function setModalGallery(work) {
  activeWork = work
  activeMediaList = getWorkMediaList(work)
  if (activeMediaList.length === 0) {
    activeMediaList = [{
      kind: "image",
      src: work?.image || "",
      poster: work?.thumbnail || "",
      link: "",
      modelFormat: "",
      sources: [],
    }]
  }
  activeMediaIndex = 0
  renderModalThumbnails()
  showModalMedia(0)
}

function shiftModalMedia(delta) {
  const next = activeMediaIndex + delta
  if (next < 0 || next >= activeMediaList.length) return
  showModalMedia(next)
}

function setModalContent(work) {
  document.getElementById("modal-title").textContent = work.title || "Untitled"
  setMetaText("modal-year", work.year)
  setMetaText("modal-type", work.type)
  setMetaText("modal-medium", work.medium)
  setMetaText("modal-size", work.size)
  setMetaText("modal-desc", work.description)
  setModalGallery(work)
}

function openAnimation(work, card) {
  const cardImage = card?.querySelector("img")
  if (!cardImage) return
  if (openTl) {
    openTl.kill()
    openTl = null
  }
  if (closeTl) {
    closeTl.kill()
    closeTl = null
  }

  activeCard = card
  setModalContent(work)
  modal.classList.add("active")
  gsap.set([modalLeftPanel, modalCloseBtn], { autoAlpha: 0, y: 18 })
  gsap.set(modal, { backgroundColor: "rgba(0,0,0,0)" })

  const canFlip = activeMediaElement instanceof HTMLImageElement
  if (!canFlip) {
    openTl = gsap.timeline({ defaults: { ease: "power3.out" } })
    openTl
      .to(modal, { backgroundColor: "rgba(0,0,0,0.9)", duration: 0.3 })
      .fromTo(modalRightPanel, { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, duration: 0.32 }, 0.08)
      .to([modalLeftPanel, modalCloseBtn], { autoAlpha: 1, y: 0, duration: 0.28, stagger: 0.03 }, 0.18)
    return
  }

  const modalImg = activeMediaElement
  gsap.set(modalImg, { autoAlpha: 0, clearProps: "all" })
  const fromRect = cardImage.getBoundingClientRect()
  const toRect = modalImg.getBoundingClientRect()
  gsap.set(modalImg, {
    position: "fixed",
    top: fromRect.top,
    left: fromRect.left,
    width: fromRect.width,
    height: fromRect.height,
    autoAlpha: 1,
    margin: 0,
    borderRadius: 8,
    zIndex: 1001,
  })

  openTl = gsap.timeline({ defaults: { ease: "power3.out" } })
  openTl
    .to(modal, { backgroundColor: "rgba(0,0,0,0.9)", duration: 0.35 })
    .to(
      modalImg,
      {
        top: toRect.top,
        left: toRect.left,
        width: toRect.width,
        height: toRect.height,
        borderRadius: 4,
        duration: 0.55,
      },
      0
    )
    .to([modalLeftPanel, modalCloseBtn], { autoAlpha: 1, y: 0, duration: 0.32, stagger: 0.04 }, 0.24)
    .add(() => gsap.set(modalImg, { clearProps: "position,top,left,width,height,margin,zIndex,borderRadius" }))
}

function closeAnimation() {
  if (closeTl) {
    closeTl.kill()
    closeTl = null
  }
  if (openTl) {
    openTl.kill()
    openTl = null
  }
  stopActiveMedia()

  const canFlipBack = activeMediaElement instanceof HTMLImageElement

  if (!canFlipBack) {
    closeTl = gsap.timeline({ defaults: { ease: "power2.inOut" } })
    closeTl
      .to([modalLeftPanel, modalCloseBtn, modalRightPanel], { autoAlpha: 0, y: 12, duration: 0.2 })
      .to(
        modal,
        {
          backgroundColor: "rgba(0,0,0,0)",
          duration: 0.25,
          onComplete: () => {
            modal.classList.remove("active")
            gsap.set([modal, modalLeftPanel, modalCloseBtn, modalRightPanel], { clearProps: "all" })
            activeCard = null
            activeMediaElement = null
            activeWork = null
            activeMediaList = []
            activeMediaIndex = 0
            if (modalMedia) modalMedia.innerHTML = ""
            if (modalThumbnails) modalThumbnails.innerHTML = ""
          },
        },
        0.02
      )
    return
  }

  const modalImg = activeMediaElement
  const targetImg = activeCard?.querySelector("img")
  const toRect = targetImg?.getBoundingClientRect()
  const fromRect = modalImg.getBoundingClientRect()
  gsap.set(modalImg, {
    position: "fixed",
    top: fromRect.top,
    left: fromRect.left,
    width: fromRect.width,
    height: fromRect.height,
    margin: 0,
    zIndex: 1001,
  })

  closeTl = gsap.timeline({ defaults: { ease: "power2.inOut" } })
  closeTl
    .to([modalLeftPanel, modalCloseBtn], { autoAlpha: 0, y: 16, duration: 0.22 })
    .to(modal, { backgroundColor: "rgba(0,0,0,0)", duration: 0.3 }, 0.06)
    .to(
      modalImg,
      {
        top: toRect ? toRect.top : fromRect.top + 20,
        left: toRect ? toRect.left : fromRect.left,
        width: toRect ? toRect.width : fromRect.width * 0.94,
        height: toRect ? toRect.height : fromRect.height * 0.94,
        autoAlpha: toRect ? 1 : 0,
        duration: 0.4,
        onComplete: () => {
          modal.classList.remove("active")
          gsap.set([modal, modalImg, modalLeftPanel, modalCloseBtn], { clearProps: "all" })
          activeCard = null
          activeMediaElement = null
          activeWork = null
          activeMediaList = []
          activeMediaIndex = 0
          if (modalMedia) modalMedia.innerHTML = ""
          if (modalThumbnails) modalThumbnails.innerHTML = ""
        },
      },
      0.02
    )
}

modalCloseBtn.addEventListener("click", closeAnimation)
modal.addEventListener("click", (event) => {
  if (event.target === modal) closeAnimation()
})
document.addEventListener("keydown", (event) => {
  if (!modal.classList.contains("active")) return
  if (event.key === "Escape") {
    closeAnimation()
    return
  }
  if (event.key === "ArrowLeft") {
    event.preventDefault()
    shiftModalMedia(-1)
  }
  if (event.key === "ArrowRight") {
    event.preventDefault()
    shiftModalMedia(1)
  }
})

modalNavPrev?.addEventListener("click", () => shiftModalMedia(-1))
modalNavNext?.addEventListener("click", () => shiftModalMedia(1))

setupFilterEvents()
setupSearchEvents()
setupImageProtection()
loadFilterConfig().then(loadWorks)
