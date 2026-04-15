import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from tkinter import BOTH, END, LEFT, W, filedialog, messagebox
import tkinter as tk
from tkinter import ttk


def _config_path() -> Path:
    return Path.home() / ".works_manager_config.json"


def _to_posix_rel(project_dir: Path, abs_path: Path) -> str:
    return abs_path.relative_to(project_dir).as_posix()


def _read_json(path: Path, default):
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


@dataclass
class Work:
    id: str
    title: str = ""
    year: str = ""
    type: str = ""
    series: str = ""
    medium: str = ""
    size: str = ""
    thumbnail: str = ""
    image: str = ""
    description: str = ""
    content_kind: str = "image"
    content_src: str = ""
    content_poster: str = ""
    content_link: str = ""
    content_model_format: str = ""

    @staticmethod
    def from_dict(d: dict) -> "Work":
        content = d.get("content", {}) if isinstance(d.get("content"), dict) else {}
        return Work(
            id=str(d.get("id", "")),
            title=str(d.get("title", "")),
            year=str(d.get("year", "")),
            type=str(d.get("type", "")),
            series=str(d.get("series", "")),
            medium=str(d.get("medium", "")),
            size=str(d.get("size", "")),
            thumbnail=str(d.get("thumbnail", "")),
            image=str(d.get("image", "")),
            description=str(d.get("description", "")),
            content_kind=str(content.get("kind", "image") or "image"),
            content_src=str(content.get("src", d.get("image", ""))),
            content_poster=str(content.get("poster", d.get("thumbnail", ""))),
            content_link=str(content.get("link", "")),
            content_model_format=str(content.get("modelFormat", "")),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "year": self.year,
            "type": self.type,
            "series": self.series,
            "medium": self.medium,
            "size": self.size,
            "thumbnail": self.thumbnail,
            "image": self.image,
            "description": self.description,
            "content": {
                "kind": self.content_kind or "image",
                "src": self.content_src or self.image,
                "poster": self.content_poster or self.thumbnail,
                "link": self.content_link,
                "modelFormat": self.content_model_format,
            },
        }


@dataclass
class Exhibition:
    id: str
    title: str = ""
    year: str = ""
    type: str = "group"
    location: str = ""
    curator: str = ""
    theme: str = ""
    cover: str = ""
    media: List[Dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "Exhibition":
        media = d.get("media", [])
        if not isinstance(media, list):
            media = []
        return Exhibition(
            id=str(d.get("id", "")),
            title=str(d.get("title", "")),
            year=str(d.get("year", "")),
            type=str(d.get("type", "group") or "group"),
            location=str(d.get("location", "")),
            curator=str(d.get("curator", "")),
            theme=str(d.get("theme", "")),
            cover=str(d.get("cover", "")),
            media=[m for m in media if isinstance(m, dict)],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "year": self.year,
            "type": self.type,
            "location": self.location,
            "curator": self.curator,
            "theme": self.theme,
            "cover": self.cover,
            "media": self.media,
        }


@dataclass
class NewsItem:
    id: str
    date: str = ""
    title: str = ""
    description: str = ""
    image: str = ""
    link: str = ""
    style: str = "featured"  # featured/text

    @staticmethod
    def from_dict(d: dict) -> "NewsItem":
        return NewsItem(
            id=str(d.get("id", "")),
            date=str(d.get("date", "")),
            title=str(d.get("title", "")),
            description=str(d.get("description", "")),
            image=str(d.get("image", "")),
            link=str(d.get("link", "")),
            style=str(d.get("style", "featured") or "featured"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "title": self.title,
            "description": self.description,
            "image": self.image,
            "link": self.link,
            "style": self.style,
        }


class WorksTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, app: "WorksManagerApp"):
        super().__init__(parent)
        self.app = app
        self.works: List[Work] = []
        self.current_index: Optional[int] = None
        self._build_ui()
        self._load_works()
        self._refresh_list()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=12)
        left.grid(row=0, column=0, sticky="ns")
        ttk.Label(left, text="作品列表", font=("Segoe UI", 11, "bold")).pack(anchor=W)

        self.listbox = tk.Listbox(left, width=38)
        self.listbox.pack(fill=BOTH, expand=True, pady=(8, 8))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="添加", command=self._on_add).pack(side=LEFT, padx=4)
        ttk.Button(btn_row, text="删除", command=self._on_delete).pack(side=LEFT, padx=4)
        self.delete_images_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text="删除对应图片文件", variable=self.delete_images_var).pack(anchor=W, pady=(8, 0))

        right = ttk.Frame(self, padding=12)
        right.grid(row=0, column=1, sticky="nsew")
        editor = ttk.Frame(right)
        editor.pack(fill=BOTH, expand=True)
        editor.grid_columnconfigure(1, weight=1)
        for c in range(1, 5):
            editor.grid_columnconfigure(c, weight=1)

        self.id_var = tk.StringVar(value="")
        self.image_var = tk.StringVar(value="")
        self.title_var = tk.StringVar(value="")
        self.year_var = tk.StringVar(value="")
        self.type_var = tk.StringVar(value="")
        self.series_var = tk.StringVar(value="")
        self.medium_var = tk.StringVar(value="")
        self.size_var = tk.StringVar(value="")
        self.content_kind_var = tk.StringVar(value="image")
        self.content_src_var = tk.StringVar(value="")
        self.content_poster_var = tk.StringVar(value="")
        self.content_link_var = tk.StringVar(value="")
        self.content_model_format_var = tk.StringVar(value="")

        ttk.Label(editor, text="ID").grid(row=0, column=0, sticky=W, padx=(0, 10))
        ttk.Entry(editor, textvariable=self.id_var, state="readonly").grid(row=0, column=1, sticky="ew")
        ttk.Label(editor, text="图片").grid(row=0, column=2, sticky=W, padx=(20, 10))
        ttk.Entry(editor, textvariable=self.image_var, state="readonly").grid(row=0, column=3, sticky="ew")
        ttk.Button(editor, text="选择图片", command=self._on_pick_image).grid(row=0, column=4, sticky="e")

        def add_entry(r, label, var):
            ttk.Label(editor, text=label).grid(row=r, column=0, sticky=W, padx=(0, 10))
            ttk.Entry(editor, textvariable=var).grid(row=r, column=1, sticky="ew", padx=(0, 10))

        def add_select(r, label, var, values):
            ttk.Label(editor, text=label).grid(row=r, column=0, sticky=W, padx=(0, 10))
            combo = ttk.Combobox(editor, textvariable=var, values=values, state="readonly")
            combo.grid(row=r, column=1, sticky="ew", padx=(0, 10))
            if values and not var.get():
                var.set(values[0])

        add_entry(1, "标题", self.title_var)
        add_entry(2, "年份", self.year_var)
        add_select(3, "类型", self.type_var, self.app.field_options["type"])
        add_select(4, "系列", self.series_var, self.app.field_options["series"])
        add_entry(5, "媒介", self.medium_var)
        add_entry(6, "尺寸(可选)", self.size_var)
        add_select(7, "内容类型", self.content_kind_var, self.app.field_options["content_kind"])
        add_entry(8, "内容源src", self.content_src_var)
        add_entry(9, "封面poster(可选)", self.content_poster_var)
        add_entry(10, "网页/3D链接link(可选)", self.content_link_var)
        add_entry(11, "3D格式(modelFormat, 可选)", self.content_model_format_var)

        ttk.Label(editor, text="文本描述").grid(row=12, column=0, sticky=W, padx=(0, 10), pady=(12, 0))
        self.desc_text = tk.Text(editor, height=10, wrap="word")
        self.desc_text.grid(row=12, column=1, columnspan=4, sticky="nsew", pady=(12, 0))
        editor.grid_rowconfigure(12, weight=1)

        action = ttk.Frame(right)
        action.pack(fill="x", pady=(10, 0))
        ttk.Button(action, text="保存当前作品", command=self._on_save).pack(side=LEFT, padx=6)
        ttk.Button(action, text="刷新列表", command=self._refresh_from_disk).pack(side=LEFT, padx=6)
        ttk.Button(action, text="编辑筛选字段(filters.json)", command=self.app._on_edit_filters).pack(side=LEFT, padx=6)

    def _load_works(self):
        raw = _read_json(self.app.works_json_path, default=[])
        self.works = [Work.from_dict(d) for d in raw if isinstance(d, dict)]

    def _save_works(self):
        _write_json(self.app.works_json_path, [w.to_dict() for w in self.works])

    def _refresh_list(self):
        self.listbox.delete(0, END)
        for w in self.works:
            label = w.title.strip() or w.id
            yr = f" ({w.year})" if w.year else ""
            self.listbox.insert(END, f"{label}{yr}")
        self.current_index = None
        self._clear_editor()

    def _clear_editor(self):
        self.id_var.set("")
        self.image_var.set("")
        self.title_var.set("")
        self.year_var.set("")
        self.type_var.set("")
        self.series_var.set("")
        self.medium_var.set("")
        self.size_var.set("")
        self.content_kind_var.set("image")
        self.content_src_var.set("")
        self.content_poster_var.set("")
        self.content_link_var.set("")
        self.content_model_format_var.set("")
        self.desc_text.delete("1.0", END)

    def _on_select(self, _evt):
        sel = self.listbox.curselection()
        if not sel:
            return
        self.current_index = int(sel[0])
        w = self.works[self.current_index]
        self.id_var.set(w.id)
        self.image_var.set(w.image)
        self.title_var.set(w.title)
        self.year_var.set(w.year)
        self.type_var.set(w.type)
        self.series_var.set(w.series)
        self.medium_var.set(w.medium)
        self.size_var.set(w.size)
        self.content_kind_var.set(w.content_kind or "image")
        self.content_src_var.set(w.content_src)
        self.content_poster_var.set(w.content_poster)
        self.content_link_var.set(w.content_link)
        self.content_model_format_var.set(w.content_model_format)
        self.desc_text.delete("1.0", END)
        self.desc_text.insert("1.0", w.description)

    def _next_id(self) -> str:
        max_num = 0
        for w in self.works:
            parts = (w.id or "").split("-")
            if len(parts) == 2 and parts[0] == "work":
                try:
                    max_num = max(max_num, int(parts[1]))
                except ValueError:
                    pass
        return f"work-{max_num + 1:03d}"

    def _on_add(self):
        w = Work(id=self._next_id())
        self.works.append(w)
        self._save_works()
        self._refresh_from_disk()

    def _on_delete(self):
        if self.current_index is None:
            messagebox.showwarning("提示", "请先选择要删除的作品。")
            return
        w = self.works[self.current_index]
        if not messagebox.askyesno("确认删除", f"确定删除《{w.title or w.id}》吗？"):
            return
        if bool(self.delete_images_var.get()):
            for rel in [w.image, w.thumbnail]:
                if not rel:
                    continue
                p = self.app.project_dir / Path(rel)
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass
        del self.works[self.current_index]
        self._save_works()
        self._refresh_from_disk()

    def _on_pick_image(self):
        if self.current_index is None:
            messagebox.showwarning("提示", "请先选择作品。")
            return
        w = self.works[self.current_index]
        chosen = filedialog.askopenfilename(
            title="选择作品图片",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.gif *.bmp"), ("All files", "*.*")],
        )
        if not chosen:
            return
        src = Path(chosen)
        if not src.exists():
            return
        self.app.works_img_dir.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower() or ".webp"
        dest = self.app.works_img_dir / f"{w.id}{ext}"
        shutil.copy2(src, dest)
        rel = _to_posix_rel(self.app.project_dir, dest)
        w.image = rel
        w.thumbnail = rel
        if not w.content_src:
            w.content_src = rel
        if not w.content_poster:
            w.content_poster = rel
        self.image_var.set(w.image)
        self.content_src_var.set(w.content_src)
        self.content_poster_var.set(w.content_poster)
        if self.app.auto_save_var.get():
            self._save_works()

    def _on_save(self):
        if self.current_index is None:
            messagebox.showwarning("提示", "请先选择作品。")
            return
        w = self.works[self.current_index]
        w.title = self.title_var.get().strip()
        w.year = self.year_var.get().strip()
        w.type = self.type_var.get().strip()
        w.series = self.series_var.get().strip()
        w.medium = self.medium_var.get().strip()
        w.size = self.size_var.get().strip()
        w.description = self.desc_text.get("1.0", END).strip()
        w.content_kind = self.content_kind_var.get().strip().lower() or "image"
        w.content_src = self.content_src_var.get().strip()
        w.content_poster = self.content_poster_var.get().strip()
        w.content_link = self.content_link_var.get().strip()
        w.content_model_format = self.content_model_format_var.get().strip().lower()
        self._save_works()
        messagebox.showinfo("成功", "已保存 works.json。")
        self._refresh_from_disk()

    def _refresh_from_disk(self):
        self._load_works()
        self._refresh_list()


class ExhibitionsTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, app: "WorksManagerApp"):
        super().__init__(parent)
        self.app = app
        self.exhibitions: List[Exhibition] = []
        self.current_index: Optional[int] = None
        self.current_media_index: Optional[int] = None
        self.media_items: List[Dict[str, Any]] = []
        self._build_ui()
        self._refresh_from_disk()

    def _autosave_if_needed(self):
        if self.app.auto_save_var.get():
            self._persist(silent=True)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        left = ttk.Frame(self, padding=12)
        left.grid(row=0, column=0, sticky="ns")
        ttk.Label(left, text="展览列表", font=("Segoe UI", 11, "bold")).pack(anchor=W)
        self.listbox = tk.Listbox(left, width=40)
        self.listbox.pack(fill=BOTH, expand=True, pady=(8, 8))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        row = ttk.Frame(left); row.pack(fill="x")
        ttk.Button(row, text="添加", command=self._on_add).pack(side=LEFT, padx=4)
        ttk.Button(row, text="删除", command=self._on_delete).pack(side=LEFT, padx=4)
        ttk.Button(row, text="刷新", command=self._refresh_from_disk).pack(side=LEFT, padx=4)

        right = ttk.Frame(self, padding=12)
        right.grid(row=0, column=1, sticky="nsew")
        editor = ttk.Frame(right)
        editor.pack(fill=BOTH, expand=True)
        editor.grid_columnconfigure(1, weight=1)

        def add_entry(r, label, var, readonly=False):
            ttk.Label(editor, text=label).grid(row=r, column=0, sticky=W, padx=(0, 10), pady=4)
            ttk.Entry(editor, textvariable=var, state="readonly" if readonly else "normal").grid(row=r, column=1, sticky="ew", pady=4)

        self.id_var = tk.StringVar(value="")
        self.title_var = tk.StringVar(value="")
        self.year_var = tk.StringVar(value="")
        self.type_var = tk.StringVar(value="group")
        self.location_var = tk.StringVar(value="")
        self.curator_var = tk.StringVar(value="")
        self.cover_var = tk.StringVar(value="")
        add_entry(0, "ID", self.id_var, True)
        add_entry(1, "名称", self.title_var)
        add_entry(2, "年份", self.year_var)
        ttk.Label(editor, text="类型").grid(row=3, column=0, sticky=W, padx=(0, 10), pady=4)
        ttk.Combobox(editor, textvariable=self.type_var, values=["solo", "group"], state="readonly").grid(row=3, column=1, sticky="ew", pady=4)
        add_entry(4, "地点", self.location_var)
        add_entry(5, "策展人", self.curator_var)
        add_entry(6, "封面cover", self.cover_var)
        ttk.Label(editor, text="主题描述").grid(row=7, column=0, sticky=W, padx=(0, 10), pady=(8, 4))
        self.theme_text = tk.Text(editor, height=5, wrap="word")
        self.theme_text.grid(row=7, column=1, sticky="ew", pady=(8, 4))

        ttk.Label(editor, text="媒体列表").grid(row=8, column=0, sticky=W, padx=(0, 10), pady=(12, 4))
        media_wrap = ttk.Frame(editor)
        media_wrap.grid(row=8, column=1, sticky="nsew")
        media_wrap.grid_columnconfigure(1, weight=1)

        left_m = ttk.Frame(media_wrap); left_m.grid(row=0, column=0, sticky="ns")
        self.media_listbox = tk.Listbox(left_m, width=34)
        self.media_listbox.pack(fill=BOTH, expand=True, pady=(0, 6))
        self.media_listbox.bind("<<ListboxSelect>>", self._on_media_select)
        mrow = ttk.Frame(left_m); mrow.pack(fill="x")
        ttk.Button(mrow, text="添加媒体", command=self._on_media_add).pack(side=LEFT, padx=4)
        ttk.Button(mrow, text="删除媒体", command=self._on_media_delete).pack(side=LEFT, padx=4)

        right_m = ttk.Frame(media_wrap); right_m.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right_m.grid_columnconfigure(1, weight=1)
        self.media_kind_var = tk.StringVar(value="image")
        self.media_caption_var = tk.StringVar(value="")
        self.media_src_var = tk.StringVar(value="")
        self.media_link_var = tk.StringVar(value="")
        self.media_poster_var = tk.StringVar(value="")
        ttk.Label(right_m, text="类型").grid(row=0, column=0, sticky=W, pady=4)
        krow = ttk.Frame(right_m); krow.grid(row=0, column=1, sticky="w", pady=4)
        for k, lbl in [("image", "Image"), ("video", "Video"), ("model", "3D"), ("web", "Web")]:
            ttk.Radiobutton(krow, text=lbl, value=k, variable=self.media_kind_var, command=self._sync_browse_state).pack(side=LEFT, padx=(0, 10))
        ttk.Label(right_m, text="caption").grid(row=1, column=0, sticky=W, pady=4)
        ttk.Entry(right_m, textvariable=self.media_caption_var).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(right_m, text="src").grid(row=2, column=0, sticky=W, pady=4)
        srow = ttk.Frame(right_m); srow.grid(row=2, column=1, sticky="ew", pady=4); srow.grid_columnconfigure(0, weight=1)
        ttk.Entry(srow, textvariable=self.media_src_var).grid(row=0, column=0, sticky="ew")
        self.media_browse_btn = ttk.Button(srow, text="浏览…", command=self._on_media_browse)
        self.media_browse_btn.grid(row=0, column=1, padx=(8, 0))
        ttk.Label(right_m, text="link").grid(row=3, column=0, sticky=W, pady=4)
        ttk.Entry(right_m, textvariable=self.media_link_var).grid(row=3, column=1, sticky="ew", pady=4)
        ttk.Label(right_m, text="poster").grid(row=4, column=0, sticky=W, pady=4)
        ttk.Entry(right_m, textvariable=self.media_poster_var).grid(row=4, column=1, sticky="ew", pady=4)
        arow = ttk.Frame(right_m); arow.grid(row=5, column=1, sticky="w", pady=(8, 0))
        ttk.Button(arow, text="应用到当前媒体项", command=self._on_media_apply).pack(side=LEFT, padx=(0, 8))
        ttk.Button(arow, text="向上", command=lambda: self._move_media(-1)).pack(side=LEFT, padx=(0, 8))
        ttk.Button(arow, text="向下", command=lambda: self._move_media(1)).pack(side=LEFT)

        editor.grid_rowconfigure(8, weight=1)
        action = ttk.Frame(right); action.pack(fill="x", pady=(8, 0))
        ttk.Button(action, text="保存当前展览", command=self._on_save).pack(side=LEFT, padx=6)

    def _read(self):
        raw = _read_json(self.app.exhibitions_json_path, [])
        self.exhibitions = [Exhibition.from_dict(d) for d in raw if isinstance(d, dict)]

    def _write(self):
        _write_json(self.app.exhibitions_json_path, [e.to_dict() for e in self.exhibitions])

    def _persist(self, silent=False):
        if self.current_index is not None and 0 <= self.current_index < len(self.exhibitions):
            e = self.exhibitions[self.current_index]
            e.title = self.title_var.get().strip()
            e.year = self.year_var.get().strip()
            e.type = self.type_var.get().strip() or "group"
            e.location = self.location_var.get().strip()
            e.curator = self.curator_var.get().strip()
            e.cover = self.cover_var.get().strip()
            e.theme = self.theme_text.get("1.0", END).strip()
            e.media = [m for m in self.media_items if isinstance(m, dict)]
        self._write()
        if not silent:
            messagebox.showinfo("成功", "已保存 exhibitions.json。")
        self._refresh_from_disk()

    def _refresh_from_disk(self):
        self._read()
        self.listbox.delete(0, END)
        for e in self.exhibitions:
            self.listbox.insert(END, f"{e.title or e.id}{f' ({e.year})' if e.year else ''}")
        self.current_index = None
        self._clear_editor()

    def _clear_editor(self):
        self.id_var.set(""); self.title_var.set(""); self.year_var.set(""); self.type_var.set("group")
        self.location_var.set(""); self.curator_var.set(""); self.cover_var.set("")
        self.theme_text.delete("1.0", END)
        self.media_items = []; self.current_media_index = None
        self._refresh_media_list(); self._clear_media_form()

    def _on_select(self, _evt):
        sel = self.listbox.curselection()
        if not sel:
            return
        self.current_index = int(sel[0])
        e = self.exhibitions[self.current_index]
        self.id_var.set(e.id); self.title_var.set(e.title); self.year_var.set(e.year); self.type_var.set(e.type or "group")
        self.location_var.set(e.location); self.curator_var.set(e.curator); self.cover_var.set(e.cover)
        self.theme_text.delete("1.0", END); self.theme_text.insert("1.0", e.theme or "")
        self.media_items = [m for m in (e.media or []) if isinstance(m, dict)]
        self.current_media_index = None
        self._refresh_media_list(); self._clear_media_form()

    def _next_id(self):
        n = 0
        for e in self.exhibitions:
            parts = (e.id or "").split("-")
            if len(parts) == 2 and parts[0] == "exh":
                try: n = max(n, int(parts[1]))
                except ValueError: pass
        return f"exh-{n+1:03d}"

    def _on_add(self):
        self.exhibitions.append(Exhibition(id=self._next_id()))
        self._autosave_if_needed() if self.app.auto_save_var.get() else self._write()
        self._refresh_from_disk()

    def _on_delete(self):
        if self.current_index is None:
            return
        del self.exhibitions[self.current_index]
        self._autosave_if_needed() if self.app.auto_save_var.get() else self._write()
        self._refresh_from_disk()

    def _media_label(self, m: Dict[str, Any], i: int):
        k = str(m.get("kind", "image"))
        t = str(m.get("caption", "") or m.get("link", "") or m.get("src", "") or "(empty)")
        if len(t) > 30: t = t[:30] + "…"
        return f"{i+1:02d}. {k} · {t}"

    def _refresh_media_list(self):
        self.media_listbox.delete(0, END)
        for i, m in enumerate(self.media_items):
            self.media_listbox.insert(END, self._media_label(m, i))

    def _clear_media_form(self):
        self.media_kind_var.set("image"); self.media_caption_var.set(""); self.media_src_var.set("")
        self.media_link_var.set(""); self.media_poster_var.set(""); self._sync_browse_state()

    def _sync_browse_state(self):
        kind = self.media_kind_var.get().lower()
        self.media_browse_btn.configure(state="normal" if kind in {"image", "video"} else "disabled")

    def _on_media_select(self, _evt):
        sel = self.media_listbox.curselection()
        if not sel:
            return
        self.current_media_index = int(sel[0])
        m = self.media_items[self.current_media_index]
        self.media_kind_var.set(str(m.get("kind", "image")))
        self.media_caption_var.set(str(m.get("caption", "")))
        self.media_src_var.set(str(m.get("src", "")))
        self.media_link_var.set(str(m.get("link", "")))
        self.media_poster_var.set(str(m.get("poster", "")))
        self._sync_browse_state()

    def _on_media_add(self):
        self.media_items.append({"kind": self.media_kind_var.get() or "image", "caption": "", "src": ""})
        self._refresh_media_list()
        idx = len(self.media_items) - 1
        self.media_listbox.selection_clear(0, END); self.media_listbox.selection_set(idx)
        self.current_media_index = idx
        self._autosave_if_needed()

    def _on_media_delete(self):
        if self.current_media_index is None: return
        if 0 <= self.current_media_index < len(self.media_items):
            del self.media_items[self.current_media_index]
        self.current_media_index = None
        self._refresh_media_list(); self._clear_media_form()
        self._autosave_if_needed()

    def _on_media_apply(self):
        if self.current_media_index is None: return
        m = {
            "kind": self.media_kind_var.get().strip().lower() or "image",
            "caption": self.media_caption_var.get().strip(),
        }
        src = self.media_src_var.get().strip()
        link = self.media_link_var.get().strip()
        poster = self.media_poster_var.get().strip()
        if src: m["src"] = src
        if link: m["link"] = link
        if poster: m["poster"] = poster
        self.media_items[self.current_media_index] = m
        self._refresh_media_list()
        self._autosave_if_needed()

    def _move_media(self, delta: int):
        if self.current_media_index is None: return
        i = self.current_media_index; j = i + delta
        if not (0 <= i < len(self.media_items) and 0 <= j < len(self.media_items)): return
        self.media_items[i], self.media_items[j] = self.media_items[j], self.media_items[i]
        self.current_media_index = j
        self._refresh_media_list()
        self.media_listbox.selection_clear(0, END); self.media_listbox.selection_set(j)
        self._autosave_if_needed()

    def _on_media_browse(self):
        kind = self.media_kind_var.get().lower()
        if kind not in {"image", "video"}: return
        if self.current_index is None: return
        exh = self.exhibitions[self.current_index]
        filetypes = [("Image files", "*.png *.jpg *.jpeg *.webp *.gif *.bmp"), ("All files", "*.*")]
        if kind == "video":
            filetypes = [("Video files", "*.mp4 *.webm *.ogg *.mov *.m4v"), ("All files", "*.*")]
        chosen = filedialog.askopenfilename(title="选择媒体文件", filetypes=filetypes)
        if not chosen: return
        src = Path(chosen)
        if not src.exists(): return
        self.app.exhibitions_img_dir.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower() or (".webp" if kind == "image" else ".mp4")
        seq = (self.current_media_index + 1) if self.current_media_index is not None else (len(self.media_items) + 1)
        dest = self.app.exhibitions_img_dir / f"{exh.id or 'exh'}-m{seq:02d}{ext}"
        shutil.copy2(src, dest)
        self.media_src_var.set(_to_posix_rel(self.app.project_dir, dest))

    def _on_save(self):
        self._persist(silent=False)


class NewsTab(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, app: "WorksManagerApp"):
        super().__init__(parent)
        self.app = app
        self.items: List[NewsItem] = []
        self.current_index: Optional[int] = None
        self._build_ui()
        self._refresh_from_disk()

    def _autosave(self):
        if self.app.auto_save_var.get():
            self._persist(silent=True)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        left = ttk.Frame(self, padding=12); left.grid(row=0, column=0, sticky="ns")
        ttk.Label(left, text="News 列表", font=("Segoe UI", 11, "bold")).pack(anchor=W)
        self.listbox = tk.Listbox(left, width=40); self.listbox.pack(fill=BOTH, expand=True, pady=(8, 8))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        r = ttk.Frame(left); r.pack(fill="x")
        ttk.Button(r, text="添加", command=self._on_add).pack(side=LEFT, padx=4)
        ttk.Button(r, text="删除", command=self._on_delete).pack(side=LEFT, padx=4)
        ttk.Button(r, text="刷新", command=self._refresh_from_disk).pack(side=LEFT, padx=4)

        right = ttk.Frame(self, padding=12); right.grid(row=0, column=1, sticky="nsew")
        editor = ttk.Frame(right); editor.pack(fill=BOTH, expand=True)
        editor.grid_columnconfigure(1, weight=1)
        self.id_var = tk.StringVar(value="")
        self.date_var = tk.StringVar(value="")
        self.title_var = tk.StringVar(value="")
        self.image_var = tk.StringVar(value="")
        self.link_var = tk.StringVar(value="")
        self.style_var = tk.StringVar(value="featured")

        def row_entry(rn, label, var, readonly=False):
            ttk.Label(editor, text=label).grid(row=rn, column=0, sticky=W, padx=(0, 10), pady=4)
            ttk.Entry(editor, textvariable=var, state="readonly" if readonly else "normal").grid(row=rn, column=1, sticky="ew", pady=4)

        row_entry(0, "ID", self.id_var, True)
        row_entry(1, "日期", self.date_var)
        row_entry(2, "标题", self.title_var)
        ttk.Label(editor, text="样式").grid(row=3, column=0, sticky=W, padx=(0, 10), pady=4)
        ttk.Combobox(editor, textvariable=self.style_var, values=["featured", "text"], state="readonly").grid(row=3, column=1, sticky="ew", pady=4)
        ttk.Label(editor, text="图片").grid(row=4, column=0, sticky=W, padx=(0, 10), pady=4)
        ir = ttk.Frame(editor); ir.grid(row=4, column=1, sticky="ew", pady=4); ir.grid_columnconfigure(0, weight=1)
        ttk.Entry(ir, textvariable=self.image_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(ir, text="浏览…", command=self._on_pick_image).grid(row=0, column=1, padx=(8, 0))
        row_entry(5, "外链 link", self.link_var)
        ttk.Label(editor, text="内容描述").grid(row=6, column=0, sticky=W, padx=(0, 10), pady=(8, 4))
        self.desc_text = tk.Text(editor, height=8, wrap="word")
        self.desc_text.grid(row=6, column=1, sticky="nsew", pady=(8, 4))
        editor.grid_rowconfigure(6, weight=1)
        a = ttk.Frame(right); a.pack(fill="x", pady=(8, 0))
        ttk.Button(a, text="保存当前 News", command=self._on_save).pack(side=LEFT, padx=6)

    def _read(self):
        raw = _read_json(self.app.news_json_path, [])
        self.items = [NewsItem.from_dict(d) for d in raw if isinstance(d, dict)]

    def _write(self):
        _write_json(self.app.news_json_path, [x.to_dict() for x in self.items])

    def _persist(self, silent=False):
        if self.current_index is not None and 0 <= self.current_index < len(self.items):
            n = self.items[self.current_index]
            n.date = self.date_var.get().strip()
            n.title = self.title_var.get().strip()
            n.style = self.style_var.get().strip() or "featured"
            n.image = self.image_var.get().strip()
            n.link = self.link_var.get().strip()
            n.description = self.desc_text.get("1.0", END).strip()
        self._write()
        if not silent:
            messagebox.showinfo("成功", "已保存 news-data/news.json。")
        self._refresh_from_disk()

    def _refresh_from_disk(self):
        self._read()
        self.listbox.delete(0, END)
        for n in self.items:
            self.listbox.insert(END, f"{n.date} · {n.title}")
        self.current_index = None
        self._clear_form()

    def _clear_form(self):
        self.id_var.set(""); self.date_var.set(""); self.title_var.set("")
        self.style_var.set("featured"); self.image_var.set(""); self.link_var.set("")
        self.desc_text.delete("1.0", END)

    def _next_id(self):
        m = 0
        for n in self.items:
            parts = (n.id or "").split("-")
            if len(parts) == 2 and parts[0] == "news":
                try: m = max(m, int(parts[1]))
                except ValueError: pass
        return f"news-{m+1:03d}"

    def _on_add(self):
        self.items.append(NewsItem(id=self._next_id()))
        self._autosave() if self.app.auto_save_var.get() else self._write()
        self._refresh_from_disk()

    def _on_delete(self):
        if self.current_index is None: return
        del self.items[self.current_index]
        self._autosave() if self.app.auto_save_var.get() else self._write()
        self._refresh_from_disk()

    def _on_select(self, _evt):
        sel = self.listbox.curselection()
        if not sel: return
        self.current_index = int(sel[0])
        n = self.items[self.current_index]
        self.id_var.set(n.id); self.date_var.set(n.date); self.title_var.set(n.title)
        self.style_var.set(n.style or "featured"); self.image_var.set(n.image); self.link_var.set(n.link)
        self.desc_text.delete("1.0", END); self.desc_text.insert("1.0", n.description)

    def _on_pick_image(self):
        if self.current_index is None: return
        chosen = filedialog.askopenfilename(
            title="选择News图片",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.gif *.bmp"), ("All files", "*.*")],
        )
        if not chosen: return
        src = Path(chosen)
        if not src.exists(): return
        self.app.news_img_dir.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower() or ".webp"
        nid = self.items[self.current_index].id or "news"
        dest = self.app.news_img_dir / f"{nid}{ext}"
        shutil.copy2(src, dest)
        self.image_var.set(_to_posix_rel(self.app.project_dir, dest))
        self._autosave()

    def _on_save(self):
        self._persist(silent=False)


class WorksManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Content Manager (Works / Exhibitions / News)")
        self.geometry("1200x760")
        self.project_dir = self._resolve_project_dir()
        self.works_json_path = self.project_dir / "works-data" / "works.json"
        self.filters_json_path = self.project_dir / "works-data" / "filters.json"
        self.exhibitions_json_path = self.project_dir / "exhibitions-data" / "exhibitions.json"
        self.news_json_path = self.project_dir / "news-data" / "news.json"
        self.works_img_dir = self.project_dir / "img" / "works"
        self.exhibitions_img_dir = self.project_dir / "img" / "exhibitions"
        self.news_img_dir = self.project_dir / "img" / "NewsFeed"
        self.field_options = self._load_field_options()
        self.auto_save_var = tk.BooleanVar(value=True)

        _write_json(self.news_json_path, _read_json(self.news_json_path, []))
        _write_json(self.exhibitions_json_path, _read_json(self.exhibitions_json_path, []))

        top = ttk.Frame(self, padding=(12, 8)); top.pack(fill="x")
        ttk.Checkbutton(top, text="自动保存（增删改时）", variable=self.auto_save_var).pack(side=LEFT)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True)
        self.works_tab = WorksTab(self.notebook, self)
        self.exhibitions_tab = ExhibitionsTab(self.notebook, self)
        self.news_tab = NewsTab(self.notebook, self)
        self.notebook.add(self.works_tab, text="Works")
        self.notebook.add(self.exhibitions_tab, text="Exhibitions")
        self.notebook.add(self.news_tab, text="News")

    def _load_field_options(self) -> Dict[str, List[str]]:
        filters = _read_json(self.filters_json_path, default={})
        groups = filters.get("groups", []) if isinstance(filters, dict) else []
        options: Dict[str, List[str]] = {}
        if isinstance(groups, list):
            for group in groups:
                if not isinstance(group, dict):
                    continue
                key = str(group.get("key", "")).strip()
                raw_opts = group.get("options", [])
                if key and isinstance(raw_opts, list):
                    options[key] = [str(v) for v in raw_opts if str(v).strip()]
        content_kinds = options.get("content_kind") or options.get("contentType") or options.get("kind") or ["image", "video", "audio", "web", "model"]
        return {"type": options.get("type", []), "series": options.get("series", []), "content_kind": content_kinds}

    def _resolve_project_dir(self) -> Path:
        cfg = _read_json(_config_path(), default={})
        cfg_dir = cfg.get("project_dir")
        if cfg_dir:
            p = Path(cfg_dir)
            if (p / "works-data" / "works.json").exists():
                return p
        cwd = Path.cwd()
        if (cwd / "works-data" / "works.json").exists():
            return cwd
        chosen = filedialog.askdirectory(title="选择项目目录（包含 works-data/works.json）")
        if not chosen:
            raise RuntimeError("未选择项目目录，程序退出。")
        chosen_path = Path(chosen)
        _write_json(_config_path(), {"project_dir": chosen_path.as_posix()})
        return chosen_path

    def _default_filters(self) -> Dict[str, Any]:
        return {
            "groups": [
                {"key": "type", "label": "Type", "options": ["painting", "mixed-media", "video", "audio", "model", "web"]},
                {"key": "series", "label": "Series", "options": []},
            ]
        }

    def _on_edit_filters(self):
        win = tk.Toplevel(self)
        win.title("编辑筛选字段（works-data/filters.json）")
        win.geometry("760x520")
        text = tk.Text(win, wrap="none")
        text.pack(fill=BOTH, expand=True, padx=12, pady=(12, 6))
        text.insert("1.0", json.dumps(_read_json(self.filters_json_path, self._default_filters()), ensure_ascii=False, indent=2))
        btns = ttk.Frame(win); btns.pack(fill="x", padx=12, pady=(0, 12))

        def on_save():
            try:
                parsed = json.loads(text.get("1.0", END).strip())
                _write_json(self.filters_json_path, parsed)
                self.field_options = self._load_field_options()
                messagebox.showinfo("成功", "filters.json 已保存")
                win.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"filters.json 格式错误：{e}")

        ttk.Button(btns, text="保存配置", command=on_save).pack(side=LEFT, padx=4)


def main():
    app = WorksManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()

