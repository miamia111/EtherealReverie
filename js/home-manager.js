window.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('works-container');
    
    if (!container) {
        console.error("找不到 works-container，请检查 HTML 里的 ID 是否正确");
        return;
    }

    // 尝试抓取 JSON
    fetch('./works-data/works.json') // 加了 ./ 确保从当前目录开始找
        .then(response => {
            if (!response.ok) throw new Error(`找不到 JSON 文件，状态码: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log("读取到的数据内容:", data);
            
            if (data.length === 0) {
                container.innerHTML = "<p>JSON 文件内没有数据</p>";
                return;
            }

            // 渲染前 4 张图
            const html = data.slice(0, 4).map(work => `
                <div class="grid-item">
                    <a href="works.html?id=${work.id}">
                        <img src="${work.image}" 
                             alt="${work.title}" 
                             style="display:block; width:100%; height:100%; background:#333;"
                             onerror="console.error('图片路径加载失败: ' + this.src)">
                    </a>
                </div>
            `).join('');

            container.innerHTML = html;
        })
        .catch(error => {
            console.error("JS 执行出错:", error);
            container.innerHTML = `<p style="color:red">加载出错: ${error.message}</p>`;
        });
});