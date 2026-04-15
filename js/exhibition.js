const list = document.getElementById("exhibitionList")
const loadingEl = document.getElementById("exhibitionLoading")
const DATA_URL = "./exhibitions-data/exhibitions.json"

function normalizeType(type){
  const v = String(type || "").trim().toLowerCase()
  if(v === "solo" || v === "group") return v
  return v || "group"
}

function escapeHtml(str){
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;")
}

function convertToEmbedUrl(url){
  if(!url) return ""
  const raw = String(url).trim()
  const yt = raw.match(/^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/)
  if(yt && yt[2] && yt[2].length === 11){
    const id = yt[2]
    return `https://www.youtube.com/embed/${id}?rel=0&showinfo=0`
  }
  if(raw.includes("vimeo.com/")){
    const id = raw.split("/").filter(Boolean).pop()
    return id ? `https://player.vimeo.com/video/${id}` : raw
  }
  return raw
}

function getDetailEl(item){
  return item?.querySelector(".exhibition-detail") || null
}

function getBannerEl(item){
  return item?.querySelector(".exhibition-banner") || null
}

function closeItem(item){
  if(!item) return
  const detail = getDetailEl(item)
  const banner = getBannerEl(item)
  if(detail){
    detail.style.maxHeight = "0px"
    detail.hidden = true
  }
  if(banner) banner.setAttribute("aria-expanded", "false")
  item.classList.remove("is-open")
}

function openItem(item){
  if(!item) return
  const detail = getDetailEl(item)
  const banner = getBannerEl(item)
  if(detail){
    detail.hidden = false
    requestAnimationFrame(()=>{
      detail.style.maxHeight = `${detail.scrollHeight}px`
    })
  }
  if(banner) banner.setAttribute("aria-expanded", "true")
  item.classList.add("is-open")
}

function toggleItem(item){
  const isOpen = item.classList.contains("is-open")
  const allItems = Array.from(list?.querySelectorAll("[data-exhibition]") || [])

  allItems.forEach((other)=>{
    if(other !== item) closeItem(other)
  })

  if(isOpen){
    closeItem(item)
  }else{
    openItem(item)
    item.scrollIntoView({block: "start", behavior: "smooth"})
  }
}

function renderMediaItem(m){
  const kind = String(m?.kind || "image").trim().toLowerCase()
  const caption = escapeHtml(m?.caption || "")
  const src = String(m?.src || "").trim()
  const link = String(m?.link || "").trim()
  const poster = String(m?.poster || "").trim()

  if(kind === "video"){
    const embed = convertToEmbedUrl(link || src)
    const safeTitle = caption ? caption : "Video"
    return `
      <figure class="exh-media-card exh-media-video">
        <div class="exh-media-frame">
          <iframe
            class="exh-media-embed"
            src="${escapeHtml(embed)}"
            title="${escapeHtml(safeTitle)}"
            loading="lazy"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
          ></iframe>
        </div>
        ${caption ? `<figcaption class="exh-media-caption">${caption}</figcaption>` : ""}
      </figure>
    `
  }

  if(kind === "model" || kind === "web"){
    const embed = convertToEmbedUrl(link || src)
    const safeTitle = caption ? caption : "Embed"
    return `
      <figure class="exh-media-card exh-media-model">
        <div class="exh-media-frame">
          <iframe
            class="exh-media-embed"
            src="${escapeHtml(embed)}"
            title="${escapeHtml(safeTitle)}"
            loading="lazy"
            referrerpolicy="strict-origin-when-cross-origin"
            allow="autoplay; fullscreen; xr-spatial-tracking"
            allowfullscreen
          ></iframe>
        </div>
        ${caption ? `<figcaption class="exh-media-caption">${caption}</figcaption>` : ""}
      </figure>
    `
  }

  // image (default)
  const imgSrc = escapeHtml(src || link)
  const alt = escapeHtml(caption || "Exhibition image")
  const posterAttr = poster ? ` data-poster="${escapeHtml(poster)}"` : ""
  return `
    <figure class="exh-media-card exh-media-image">
      <button class="exh-media-imageBtn" type="button" data-lightbox="${imgSrc}"${posterAttr} aria-label="View image">
        <img class="exh-media-img" src="${imgSrc}" alt="${alt}" loading="lazy">
      </button>
      ${caption ? `<figcaption class="exh-media-caption">${caption}</figcaption>` : ""}
    </figure>
  `
}

function renderExhibitionItem(exh, index){
  const id = String(exh?.id || `exh-${index + 1}`)
  const title = String(exh?.title || "Untitled")
  const year = String(exh?.year || "")
  const type = normalizeType(exh?.type)
  const typeLabel = type === "solo" ? "Solo" : "Group"
  const cover = String(exh?.cover || "").trim()
  const location = String(exh?.location || "").trim()
  const curator = String(exh?.curator || "").trim()
  const theme = String(exh?.theme || "").trim()
  const media = Array.isArray(exh?.media) ? exh.media : []

  const detailId = `${id}-detail`
  const bgStyle = cover ? `style="background-image:url('${escapeHtml(cover)}');"` : ""

  return `
    <article class="exhibition-item" data-exhibition data-exh-id="${escapeHtml(id)}">
      <button class="exhibition-banner" type="button" aria-expanded="false" aria-controls="${escapeHtml(detailId)}">
        <span class="exhibition-banner-bg" ${bgStyle}></span>
        <span class="exhibition-tag" aria-hidden="true">${typeLabel}</span>
        <span class="exhibition-titlewrap">
          <span class="exhibition-title">${escapeHtml(title)}</span>
          <span class="exhibition-year">${escapeHtml(year)}</span>
        </span>
      </button>

      <div class="exhibition-detail" id="${escapeHtml(detailId)}" role="region" aria-label="Exhibition details" hidden>
        <div class="exhibition-detail-inner">
          <div class="exh-detail-header">
            <div class="exh-detail-title">
              <h2 class="exh-h2">${escapeHtml(title)}</h2>
              <div class="exh-subline">
                ${year ? `<span class="exh-pill">${escapeHtml(year)}</span>` : ""}
                <span class="exh-pill">${typeLabel}</span>
              </div>
            </div>
            <div class="exh-detail-meta">
              ${location ? `<div class="exh-metaRow"><div class="exh-metaKey">Location</div><div class="exh-metaVal">${escapeHtml(location)}</div></div>` : ""}
              ${curator ? `<div class="exh-metaRow"><div class="exh-metaKey">Curator</div><div class="exh-metaVal">${escapeHtml(curator)}</div></div>` : ""}
            </div>
          </div>

          ${theme ? `<div class="exh-detail-theme">${escapeHtml(theme)}</div>` : ""}

          ${media.length > 0 ? `
            <div class="exh-mediaGrid">
              ${media.map(renderMediaItem).join("")}
            </div>
          ` : `<div class="exh-empty">暂无媒体内容</div>`}
        </div>
      </div>
    </article>
  `
}

function ensureLightbox(){
  if(document.getElementById("exhLightbox")) return
  const el = document.createElement("div")
  el.id = "exhLightbox"
  el.className = "exh-lightbox"
  el.hidden = true
  el.innerHTML = `
    <div class="exh-lightbox-backdrop" data-close></div>
    <div class="exh-lightbox-panel" role="dialog" aria-modal="true" aria-label="Image preview">
      <button class="exh-lightbox-close" type="button" data-close aria-label="Close">×</button>
      <img class="exh-lightbox-img" alt="">
    </div>
  `
  document.body.appendChild(el)

  const close = ()=>{
    el.hidden = true
    const img = el.querySelector(".exh-lightbox-img")
    if(img) img.removeAttribute("src")
  }
  el.addEventListener("click",(evt)=>{
    const t = evt.target instanceof Element ? evt.target : null
    if(t?.matches("[data-close]")) close()
  })
  document.addEventListener("keydown",(evt)=>{
    if(evt.key === "Escape" && !el.hidden) close()
  })
}

function openLightbox(src){
  ensureLightbox()
  const el = document.getElementById("exhLightbox")
  if(!el) return
  const img = el.querySelector(".exh-lightbox-img")
  if(img) img.setAttribute("src", src)
  el.hidden = false
}

async function loadExhibitions(){
  if(!list) return
  try{
    const res = await fetch(DATA_URL, {cache: "no-store"})
    if(!res.ok) throw new Error(`Failed to load exhibitions.json: ${res.status}`)
    const data = await res.json()
    const exhibitions = Array.isArray(data) ? data : []

    list.innerHTML = exhibitions.map(renderExhibitionItem).join("")
    return
  }catch(err){
    console.warn(err)
    if(loadingEl) loadingEl.textContent = "Failed to load exhibitions."
  }
}

if(list){
  list.addEventListener("click",(event)=>{
    const target = event.target instanceof Element ? event.target : null
    if(!target) return

    const lightboxBtn = target.closest(".exh-media-imageBtn")
    if(lightboxBtn){
      const src = lightboxBtn.getAttribute("data-lightbox")
      if(src) openLightbox(src)
      return
    }

    const banner = target.closest(".exhibition-banner")
    if(!banner) return
    const item = banner.closest("[data-exhibition]")
    if(!item) return
    toggleItem(item)
  })

  window.addEventListener("resize", ()=>{
    const openItemEl = list.querySelector(".exhibition-item.is-open")
    if(!openItemEl) return
    const detail = getDetailEl(openItemEl)
    if(!detail || detail.hidden) return
    detail.style.maxHeight = `${detail.scrollHeight}px`
  })
}

loadExhibitions()

