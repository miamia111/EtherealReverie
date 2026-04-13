window.addEventListener('load', () => {
    const container = document.getElementById('works-container');
    let allWorks = []; // 存储所有作品数据

    if (!container) return;

    fetch('works-data/works.json')
        .then(res => res.json())
        .then(data => {
            allWorks = data;
            // 1. 初始化显示前 4 个作品
            renderInitialWorks(allWorks.slice(0, 4));
            
            // 2. 启动随机滚动替换逻辑
            if (allWorks.length > 4) {
                setInterval(randomSwapWork, 6000); // 每 4 秒尝试替换一张图
            }
        });

    // 渲染初始 3 张图
    function renderInitialWorks(works) {
        // 只取前 3 张作品
        container.innerHTML = works.slice(0, 3).map((work, index) => `
            <div class="grid-item" id="work-slot-${index}" data-current-id="${work.id}">
                <a href="works.html?id=${work.id}">
                    <img src="${work.image}" alt="${work.title}">
                </a>
            </div>
        `).join('');
    }

    // 随机替换逻辑
    function randomSwapWork() {
        // 随机选一个格子 (0-3)
        const slotIndex = Math.floor(Math.random() * 4);
        const slot = document.getElementById(`work-slot-${slotIndex}`);
        
        // 获取当前格子没在显示的随机作品
        const currentIds = Array.from(document.querySelectorAll('.grid-item')).map(el => el.dataset.currentId);
        const availableWorks = allWorks.filter(w => !currentIds.includes(w.id));
        
        if (availableWorks.length > 0) {
            const nextWork = availableWorks[Math.floor(Math.random() * availableWorks.length)];
            
            // 执行切换动画
            const link = slot.querySelector('a');
            const img = slot.querySelector('img');
            
            img.style.opacity = '0'; // 渐隐
            
           // 步骤 2: 等淡出动画进行到一半以上时再换源 (1200ms的动画，建议等 1000ms)
        setTimeout(() => {
            slot.dataset.currentId = nextWork.id;
            link.href = `works.html?id=${nextWork.id}`;
            img.src = nextWork.image;

            // 步骤 3: 图片下载并加载完成后再淡入
            img.onload = () => {
                img.style.opacity = '1';
            };
        }, 1000);
        }
    }
});