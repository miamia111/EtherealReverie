// Load works data
// 核心 DOM
const worksGrid = document.getElementById("worksGrid")
const modal = document.getElementById("worksModal")
const modalImg = document.getElementById("modal-img")

// 作品数据
const mdFiles = [
  "./works-data/Ophelia.md",
  "./works-data/Ophanim.md"
]

let works = []

async function loadWorks(){
  // 1) 优先加载更稳的 JSON（避免前端解析 MD 失败导致列表为空）
  try{
    const res = await fetch("./works-data/works.json")
    if(!res.ok){
      throw new Error(`Failed to load works.json: ${res.status}`)
    }
    const data = await res.json()
    works = Array.isArray(data) ? data : []
    renderWorks(works)
    return
  }catch(err){
    console.error(err)
  }

  // 2) JSON 加载失败后，才退回解析 MD front-matter
  works = []
  for(const file of mdFiles){
    try{
      const res = await fetch(file)
      if(!res.ok){
        throw new Error(`Failed to load works data: ${file} (${res.status})`)
      }
      const text = await res.text()
      const parts = text.split('---')
      if(parts.length < 3) continue

      const metaRaw = parts[1]
      const content  = parts.slice(2).join('---') // 防止 description 里也出现 '---'

      const meta = {}
      metaRaw.split('\n').forEach(line=>{
        const [key,value] = line.split(':')
        if(key && value) meta[key.trim()] = value.trim()
      })

      meta.description = content.trim()
      works.push(meta)
    }catch(err){
      console.error(err)
    }
  }

  renderWorks(works)
}

function renderWorks(list){
  worksGrid.innerHTML = ""
  if(!Array.isArray(list) || list.length === 0){
    worksGrid.innerHTML = `<p style="color:#fff;opacity:.8;">暂无作品数据（请检查控制台的加载错误）</p>`
    return
  }
  list.forEach(w=>{
    const card = document.createElement("div")
    card.className = "work-card"
    card.setAttribute("data-type", w.type)
    card.setAttribute("data-series", w.series)
    card.innerHTML = `
      <img src="${w.thumbnail}" alt="${w.title}">
      <div class="work-meta"><strong>${w.title}</strong> · ${w.year}</div>
    `
    card.addEventListener("click",()=>{
      openAnimation(w,card)
    })
    worksGrid.appendChild(card)
  })
}

function openAnimation(work,card){
  const leftContent = document.getElementById("modal-left")
  const midTitle = document.getElementById("modal-title")
  const midYear = document.getElementById("modal-year")
  const midType = document.getElementById("modal-type")
  const midMedium = document.getElementById("modal-medium")
  const midSize =document.getElementById("modal-size")
  const midDesc = document.getElementById("modal-desc")

  leftContent.style.opacity = 0

  modal.classList.add("active")

  modalImg.src = work.image
  midTitle.textContent = work.title
  midYear.textContent = `${work.year}` 
  midType.textContent = `${work.type}`
  midMedium.textContent = work.medium ?? ""
  midSize.textContent = work.size ?? ""
  midDesc.textContent = work.description ?? ""

  const rect = card.querySelector("img").getBoundingClientRect()

  gsap.set(modalImg,{
    position:"fixed",
    top:rect.top,
    left:rect.left,
    width:rect.width,
    height:rect.height
  })

  gsap.to(modalImg,{
    top: "50%",
    left:"0%",
    xPercent:0,
    yPercent:0,
    width:"100%", 
    height:"auto",
    duration:0.6,
    ease:"power2.out",
    onComplete:()=>{
      modalImg.style.position="static"
      gsap.to(leftContent,{opacity:1,duration:0.4})
    }
  })
}

document.querySelector(".modal-close").addEventListener("click",()=>{

  const currentLeft = document.getElementById("modal-left")
  gsap.to(currentLeft,{opacity:0,duration:0.3})

  gsap.to(modalImg,{
    opacity:0,
    duration:0.4,
    onComplete:()=>{
      modal.classList.remove("active")
      modalImg.style.opacity = 1
    }
  })

})

loadWorks()