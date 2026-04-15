# Works Manager（简易作品管理器）

这个工具是一个桌面版（可打包成 `exe`）的简易管理器，用来维护站点源数据。

当前版本是**单窗口三标签页**：

- `Works`（`works-data/works.json`）
- `Exhibitions`（`exhibitions-data/exhibitions.json`）
- `News`（`news-data/news.json`）

可开启「自动保存（增删改时）」。

## 功能

- 添加作品记录
- 在作品详情里编辑文本描述（以及常用字段：标题、年份、类型、系列、媒介、尺寸）
- 选择图片并将其复制到 `img/works/`（图片路径会写回 `works.json`）
- 删除作品（可选：同时删除对应图片文件）
- 编辑多媒体字段：`content.kind/src/poster/link/modelFormat`
  - 可用于图片、动图、视频、音频、网页链接、3D外链预览
- 编辑筛选配置：`works-data/filters.json`（可增删顶部筛选字段和选项）
- 在 `Exhibitions` 标签管理展览数据：
  - 字段：名称/年份/类型(solo/group)/地点/策展人/主题描述/横幅封面cover
  - `media` 为可视化列表：支持添加/删除、类型单选、caption、src/link、本地浏览复制
- 在 `News` 标签管理首页 News Feed：
  - 支持添加/删除 News 条目
  - 支持外链（首页会显示跳转图标）
  - 图片浏览会自动复制到 `img/NewsFeed/`

## 运行前提

- 已安装 Python（建议 3.9+）
- 默认使用 Tkinter（Windows 一般自带）

## 直接运行（开发调试）

在项目根目录执行：

```bash
python .\tools\works_manager.py
```

首次启动会提示你选择项目目录（确保包含 `works-data/works.json`），然后会记住该路径。

## 打包成 EXE（PyInstaller）

1. 安装 PyInstaller：
   ```bash
   pip install pyinstaller
   ```
2. 在项目根目录执行：
   ```bash
   pyinstaller --onefile --noconsole --name WorksManager .\tools\works_manager.py
   ```
3. 打包产物在 `dist/WorksManager.exe`

> 注意：打包后请保证在你选择的项目目录里存在 `works-data/works.json`，否则程序会启动时要求你重新选择目录。

## 保存后如何查看效果

- 打开/刷新 `works.html`
- 打开/刷新 `exhibition.html`
- 打开/刷新 `index.html`（News Feed）
- 如果你是用浏览器直接打开 `file://`，`fetch` 可能会失败；建议用本地服务器访问（如 VS Code Live Server）。
- `works.html` 会读取：
  - `works-data/works.json`（作品数据）
  - `works-data/filters.json`（筛选按钮配置）
- `exhibition.html` 会读取：
  - `exhibitions-data/exhibitions.json`（展览数据）
- `index.html` 会读取：
  - `news-data/news.json`（News Feed 数据）

