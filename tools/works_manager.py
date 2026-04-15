import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    W,
    messagebox,
    filedialog,
)
import tkinter as tk
from tkinter import ttk


def _app_dir() -> Path:
    # When packaged with PyInstaller, sys._MEIPASS points to a temp folder.
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base)
    return Path(__file__).resolve().parent


def _config_path() -> Path:
    # Put config in user home so the EXE can be used from any folder.
    return Path.home() / ".works_manager_config.json"


def _to_posix_rel(project_dir: Path, abs_path: Path) -> str:
    # works.js uses these values inside HTML; keep forward slashes.
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
    type: str = "group"  # solo/group
    location: str = ""
    curator: str = ""
    theme: str = ""
    cover: str = ""
    media: List[Dict[str, Any]] = None

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
            "type": (self.type or "group").lower(),
            "location": self.location,
            "curator": self.curator,
            "theme": self.theme,
            "cover": self.cover,
            "media": self.media if isinstance(self.media, list) else [],
        }


class ExhibitionsManager(tk.Toplevel):
    def __init__(self, master: "WorksManagerApp"):
        super().__init__(master)
        self.master_app = master
        self.project_dir = master.project_dir
        self.exhibitions_json_path = self.project_dir / "exhibitions-data" / "exhibitions.json"
        self.title("Exhibitions Manager (exhibitions-data/exhibitions.json)")
        self.geometry("1040x700")

        self.exhibitions: List[Exhibition] = []
        self.current_index: Optional[int] = None
        self.current_media_index: Optional[int] = None
        self.media_items: List[Dict[str, Any]] = []
        self.exhibitions_img_dir = self.project_dir / "img" / "exhibitions"

        self._build_ui()
        self._load_exhibitions()
        self._refresh_list()

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

        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="添加", command=self._on_add).pack(side=LEFT, padx=4)
        ttk.Button(btn_row, text="删除", command=self._on_delete).pack(side=LEFT, padx=4)
        ttk.Button(btn_row, text="刷新", command=self._refresh_from_disk).pack(side=LEFT, padx=4)

        right = ttk.Frame(self, padding=12)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        editor = ttk.Frame(right)
        editor.grid(row=0, column=0, sticky="nsew")

        def add_entry(r, label, var, readonly=False):
            ttk.Label(editor, text=label).grid(row=r, column=0, sticky=W, padx=(0, 10), pady=4)
            state = "readonly" if readonly else "normal"
            ttk.Entry(editor, textvariable=var, state=state).grid(row=r, column=1, sticky="ew", pady=4)

        editor.grid_columnconfigure(1, weight=1)

        self.id_var = tk.StringVar(value="")
        self.title_var = tk.StringVar(value="")
        self.year_var = tk.StringVar(value="")
        self.type_var = tk.StringVar(value="group")
        self.location_var = tk.StringVar(value="")
        self.curator_var = tk.StringVar(value="")
        self.cover_var = tk.StringVar(value="")

        add_entry(0, "ID", self.id_var, readonly=True)
        add_entry(1, "名称", self.title_var)
        add_entry(2, "年份", self.year_var)

        ttk.Label(editor, text="类型").grid(row=3, column=0, sticky=W, padx=(0, 10), pady=4)
        ttk.Combobox(editor, textvariable=self.type_var, values=["solo", "group"], state="readonly").grid(
            row=3, column=1, sticky="ew", pady=4
        )
        add_entry(4, "地点", self.location_var)
        add_entry(5, "策展人", self.curator_var)
        add_entry(6, "横幅封面cover(相对路径)", self.cover_var)

        ttk.Label(editor, text="主题/展览文字").grid(row=7, column=0, sticky=W, padx=(0, 10), pady=(12, 4))
        self.theme_text = tk.Text(editor, height=6, wrap="word")
        self.theme_text.grid(row=7, column=1, sticky="nsew", pady=(12, 4))

        ttk.Label(editor, text="媒体 media[]").grid(row=8, column=0, sticky=W, padx=(0, 10), pady=(12, 6))

        media_wrap = ttk.Frame(editor)
        media_wrap.grid(row=8, column=1, sticky="nsew", pady=(12, 4))
        media_wrap.grid_columnconfigure(0, weight=0)
        media_wrap.grid_columnconfigure(1, weight=1)
        media_wrap.grid_rowconfigure(0, weight=1)

        # Left: media list + add/delete
        media_left = ttk.Frame(media_wrap)
        media_left.grid(row=0, column=0, sticky="ns")
        ttk.Label(media_left, text="媒体列表").pack(anchor=W)
        self.media_listbox = tk.Listbox(media_left, width=34)
        self.media_listbox.pack(fill=BOTH, expand=True, pady=(6, 6))
        self.media_listbox.bind("<<ListboxSelect>>", self._on_media_select)

        media_btns = ttk.Frame(media_left)
        media_btns.pack(fill="x")
        ttk.Button(media_btns, text="添加媒体", command=self._on_media_add).pack(side=LEFT, padx=4)
        ttk.Button(media_btns, text="删除媒体", command=self._on_media_delete).pack(side=LEFT, padx=4)

        # Right: media editor
        media_right = ttk.Frame(media_wrap)
        media_right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        media_right.grid_columnconfigure(1, weight=1)

        self.media_kind_var = tk.StringVar(value="image")
        self.media_src_var = tk.StringVar(value="")
        self.media_link_var = tk.StringVar(value="")
        self.media_poster_var = tk.StringVar(value="")
        self.media_caption_var = tk.StringVar(value="")

        ttk.Label(media_right, text="类型").grid(row=0, column=0, sticky=W, pady=4)
        kind_row = ttk.Frame(media_right)
        kind_row.grid(row=0, column=1, sticky="w", pady=4)
        for k, label in [("image", "Image"), ("video", "Video"), ("model", "3D Model"), ("web", "Web")]:
            ttk.Radiobutton(
                kind_row,
                text=label,
                value=k,
                variable=self.media_kind_var,
                command=self._on_media_kind_change,
            ).pack(side=LEFT, padx=(0, 10))

        ttk.Label(media_right, text="caption（一句话简介）").grid(row=1, column=0, sticky=W, pady=4)
        ttk.Entry(media_right, textvariable=self.media_caption_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(media_right, text="src（本地文件/相对路径）").grid(row=2, column=0, sticky=W, pady=4)
        src_row = ttk.Frame(media_right)
        src_row.grid(row=2, column=1, sticky="ew", pady=4)
        src_row.grid_columnconfigure(0, weight=1)
        ttk.Entry(src_row, textvariable=self.media_src_var).grid(row=0, column=0, sticky="ew")
        self._media_browse_btn = ttk.Button(src_row, text="浏览…", command=self._on_media_browse)
        self._media_browse_btn.grid(row=0, column=1, padx=(8, 0))

        ttk.Label(media_right, text="link（外链/Embed）").grid(row=3, column=0, sticky=W, pady=4)
        ttk.Entry(media_right, textvariable=self.media_link_var).grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(media_right, text="poster（可选）").grid(row=4, column=0, sticky=W, pady=4)
        ttk.Entry(media_right, textvariable=self.media_poster_var).grid(row=4, column=1, sticky="ew", pady=4)

        media_action = ttk.Frame(media_right)
        media_action.grid(row=5, column=1, sticky="w", pady=(10, 0))
        ttk.Button(media_action, text="应用到当前媒体项", command=self._on_media_apply).pack(side=LEFT, padx=(0, 8))
        ttk.Button(media_action, text="向上", command=lambda: self._move_media(-1)).pack(side=LEFT, padx=(0, 8))
        ttk.Button(media_action, text="向下", command=lambda: self._move_media(1)).pack(side=LEFT)

        editor.grid_rowconfigure(7, weight=0)
        editor.grid_rowconfigure(8, weight=1)
        media_right.grid_rowconfigure(6, weight=1)

        action = ttk.Frame(right)
        action.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(action, text="保存当前展览", command=self._on_save).pack(side=LEFT, padx=6)
        ttk.Button(action, text="提示：刷新 exhibition.html 查看效果", command=self._on_hint).pack(side=LEFT, padx=6)

    def _read(self):
        raw = _read_json(self.exhibitions_json_path, default=[])
        if not isinstance(raw, list):
            raw = []
        self.exhibitions = [Exhibition.from_dict(d) for d in raw if isinstance(d, dict)]

    def _write(self):
        _write_json(self.exhibitions_json_path, [e.to_dict() for e in self.exhibitions])

    def _load_exhibitions(self):
        self._read()

    def _refresh_list(self):
        self.listbox.delete(0, END)
        for e in self.exhibitions:
            label = e.title.strip() or e.id
            yr = f" ({e.year})" if e.year else ""
            self.listbox.insert(END, f"{label}{yr}")
        self.current_index = None
        self._clear_editor()

    def _clear_editor(self):
        self.id_var.set("")
        self.title_var.set("")
        self.year_var.set("")
        self.type_var.set("group")
        self.location_var.set("")
        self.curator_var.set("")
        self.cover_var.set("")
        self.theme_text.delete("1.0", END)
        self.media_items = []
        self.current_media_index = None
        self._refresh_media_list()
        self._clear_media_editor()

    def _next_id(self) -> str:
        max_num = 0
        for e in self.exhibitions:
            parts = (e.id or "").split("-")
            if len(parts) == 2 and parts[0] == "exh":
                try:
                    max_num = max(max_num, int(parts[1]))
                except ValueError:
                    pass
        return f"exh-{max_num + 1:03d}"

    def _on_add(self):
        new_id = self._next_id()
        e = Exhibition(id=new_id, media=[])
        self.exhibitions.append(e)
        self._write()
        self._refresh_from_disk()

        for i, item in enumerate(self.exhibitions):
            if item.id == new_id:
                self.listbox.selection_clear(0, END)
                self.listbox.selection_set(i)
                self.listbox.activate(i)
                self.current_index = i
                self._fill_editor(self.exhibitions[i])
                break

    def _on_delete(self):
        if self.current_index is None:
            messagebox.showwarning("提示", "请先选择要删除的展览。")
            return
        e = self.exhibitions[self.current_index]
        if not messagebox.askyesno("确认删除", f"确定删除《{e.title or e.id}》吗？"):
            return
        del self.exhibitions[self.current_index]
        try:
            self._write()
            self._refresh_from_disk()
            messagebox.showinfo("成功", "已删除并更新 exhibitions.json。")
        except Exception as ex:
            messagebox.showerror("错误", f"删除失败：{ex}")

    def _refresh_from_disk(self):
        try:
            self._read()
            self._refresh_list()
        except Exception as ex:
            messagebox.showerror("错误", f"加载失败：{ex}")

    def _on_select(self, _evt):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        self.current_index = idx
        self._fill_editor(self.exhibitions[idx])

    def _fill_editor(self, e: Exhibition):
        self.id_var.set(e.id)
        self.title_var.set(e.title)
        self.year_var.set(e.year)
        self.type_var.set((e.type or "group").lower())
        self.location_var.set(e.location)
        self.curator_var.set(e.curator)
        self.cover_var.set(e.cover)
        self.theme_text.delete("1.0", END)
        self.theme_text.insert("1.0", e.theme or "")
        self.media_items = [m for m in (e.media or []) if isinstance(m, dict)]
        self.current_media_index = None
        self._refresh_media_list()
        self._clear_media_editor()

    def _media_label(self, m: Dict[str, Any], idx: int) -> str:
        kind = str(m.get("kind", "image") or "image").lower()
        caption = str(m.get("caption", "") or "").strip()
        src = str(m.get("src", "") or "").strip()
        link = str(m.get("link", "") or "").strip()
        main = caption or (link or src) or "(empty)"
        if len(main) > 32:
            main = main[:32] + "…"
        return f"{idx + 1:02d}. {kind} · {main}"

    def _refresh_media_list(self):
        if not hasattr(self, "media_listbox"):
            return
        self.media_listbox.delete(0, END)
        for i, m in enumerate(self.media_items):
            self.media_listbox.insert(END, self._media_label(m, i))

    def _clear_media_editor(self):
        self.media_kind_var.set("image")
        self.media_caption_var.set("")
        self.media_src_var.set("")
        self.media_link_var.set("")
        self.media_poster_var.set("")
        self._on_media_kind_change()

    def _on_media_select(self, _evt):
        sel = self.media_listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        self.current_media_index = idx
        m = self.media_items[idx] if 0 <= idx < len(self.media_items) else {}
        self.media_kind_var.set(str(m.get("kind", "image") or "image").lower())
        self.media_caption_var.set(str(m.get("caption", "") or ""))
        self.media_src_var.set(str(m.get("src", "") or ""))
        self.media_link_var.set(str(m.get("link", "") or ""))
        self.media_poster_var.set(str(m.get("poster", "") or ""))
        self._on_media_kind_change()

    def _on_media_kind_change(self):
        # For model/web, browsing local files usually doesn't apply.
        kind = (self.media_kind_var.get() or "image").lower()
        browse_state = "normal" if kind in {"image", "video"} else "disabled"
        if hasattr(self, "_media_browse_btn"):
            self._media_browse_btn.configure(state=browse_state)

    def _on_media_add(self):
        kind = (self.media_kind_var.get() or "image").lower()
        m: Dict[str, Any] = {"kind": kind, "caption": "", "src": "", "link": "", "poster": ""}
        self.media_items.append(m)
        self._refresh_media_list()
        idx = len(self.media_items) - 1
        self.media_listbox.selection_clear(0, END)
        self.media_listbox.selection_set(idx)
        self.media_listbox.activate(idx)
        self.current_media_index = idx
        self._on_media_select(None)

    def _on_media_delete(self):
        if self.current_media_index is None:
            messagebox.showwarning("提示", "请先选择要删除的媒体项。")
            return
        idx = self.current_media_index
        if not (0 <= idx < len(self.media_items)):
            return
        del self.media_items[idx]
        self.current_media_index = None
        self._refresh_media_list()
        self._clear_media_editor()

    def _on_media_apply(self):
        if self.current_media_index is None:
            messagebox.showwarning("提示", "请先选择一个媒体项再应用。")
            return
        idx = self.current_media_index
        if not (0 <= idx < len(self.media_items)):
            return
        kind = (self.media_kind_var.get() or "image").lower()
        m = self.media_items[idx]
        m["kind"] = kind
        caption = self.media_caption_var.get().strip()
        src = self.media_src_var.get().strip()
        link = self.media_link_var.get().strip()
        poster = self.media_poster_var.get().strip()

        # Normalize: for model/web prefer link; for image prefer src.
        m["caption"] = caption
        m["src"] = src
        m["link"] = link
        if poster:
            m["poster"] = poster
        else:
            m.pop("poster", None)

        # Clean empty keys
        for k in ["src", "link"]:
            if not str(m.get(k, "")).strip():
                m.pop(k, None)

        self._refresh_media_list()
        self.media_listbox.selection_clear(0, END)
        self.media_listbox.selection_set(idx)

    def _move_media(self, delta: int):
        if self.current_media_index is None:
            return
        idx = self.current_media_index
        new_idx = idx + delta
        if not (0 <= idx < len(self.media_items)) or not (0 <= new_idx < len(self.media_items)):
            return
        self.media_items[idx], self.media_items[new_idx] = self.media_items[new_idx], self.media_items[idx]
        self.current_media_index = new_idx
        self._refresh_media_list()
        self.media_listbox.selection_clear(0, END)
        self.media_listbox.selection_set(new_idx)
        self.media_listbox.activate(new_idx)

    def _on_media_browse(self):
        kind = (self.media_kind_var.get() or "image").lower()
        if kind not in {"image", "video"}:
            return
        if self.current_index is None:
            messagebox.showwarning("提示", "请先选择一个展览（用于生成文件名）。")
            return
        exh = self.exhibitions[self.current_index]
        exh_id = exh.id or "exh"

        if kind == "image":
            filetypes = [("Image files", "*.png *.jpg *.jpeg *.webp *.gif *.bmp"), ("All files", "*.*")]
        else:
            filetypes = [("Video files", "*.mp4 *.webm *.ogg *.mov *.m4v"), ("All files", "*.*")]

        chosen = filedialog.askopenfilename(title="选择媒体文件", filetypes=filetypes)
        if not chosen:
            return
        try:
            src_path = Path(chosen)
            if not src_path.exists():
                return
            self.exhibitions_img_dir.mkdir(parents=True, exist_ok=True)
            ext = src_path.suffix.lower() or (".webp" if kind == "image" else ".mp4")
            # Use index or next sequence to avoid overwriting too often.
            seq = (self.current_media_index + 1) if self.current_media_index is not None else (len(self.media_items) + 1)
            dest_name = f"{exh_id}-m{seq:02d}{ext}"
            dest_abs = self.exhibitions_img_dir / dest_name
            shutil.copy2(src_path, dest_abs)
            rel = _to_posix_rel(self.project_dir, dest_abs)
            self.media_src_var.set(rel)
        except Exception as ex:
            messagebox.showerror("错误", f"复制媒体文件失败：{ex}")

    def _on_hint(self):
        messagebox.showinfo("提示", "保存后请刷新 exhibition.html 查看列表变化。")

    def _on_save(self):
        if self.current_index is None:
            messagebox.showwarning("提示", "请先选择或添加展览。")
            return
        e = self.exhibitions[self.current_index]
        e.title = self.title_var.get().strip()
        e.year = self.year_var.get().strip()
        e.type = (self.type_var.get().strip().lower() or "group")
        e.location = self.location_var.get().strip()
        e.curator = self.curator_var.get().strip()
        e.cover = self.cover_var.get().strip()
        e.theme = self.theme_text.get("1.0", END).strip()
        # Apply the current media editor fields (if any) before saving, but don't force.
        # Users can keep a partially edited item and apply later.
        e.media = [m for m in self.media_items if isinstance(m, dict)]

        try:
            self._write()
            messagebox.showinfo("成功", "已保存。刷新 exhibition.html 查看效果。")
            self._refresh_from_disk()
        except Exception as ex:
            messagebox.showerror("错误", f"保存失败：{ex}")


class WorksManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Works Manager (works-data/works.json)")
        self.geometry("980x620")

        self.project_dir = self._resolve_project_dir()
        self.works_json_path = self.project_dir / "works-data" / "works.json"
        self.filters_json_path = self.project_dir / "works-data" / "filters.json"
        self.works_img_dir = self.project_dir / "img" / "works"
        self.exhibitions_json_path = self.project_dir / "exhibitions-data" / "exhibitions.json"
        self.field_options = self._load_field_options()

        self.works: List[Work] = []
        self.current_index: Optional[int] = None

        self._build_ui()
        self._load_works()
        self._refresh_list()

    def _open_exhibitions_manager(self):
        # Create file if missing so the manager can open cleanly.
        if not self.exhibitions_json_path.exists():
            try:
                _write_json(self.exhibitions_json_path, [])
            except Exception as e:
                messagebox.showerror("错误", f"无法创建 exhibitions.json：{e}")
                return
        ExhibitionsManager(self)

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
                if not key or not isinstance(raw_opts, list):
                    continue
                options[key] = [str(v) for v in raw_opts if str(v).strip()]

        # Optional key in filters.json; fallback to fixed content kinds.
        content_kinds = (
            options.get("content_kind")
            or options.get("contentType")
            or options.get("kind")
            or ["image", "video", "audio", "web", "model"]
        )
        return {
            "type": options.get("type", []),
            "series": options.get("series", []),
            "content_kind": content_kinds,
        }

    def _resolve_project_dir(self) -> Path:
        cfg = _read_json(_config_path(), default={})
        cfg_dir = cfg.get("project_dir")
        if cfg_dir:
            p = Path(cfg_dir)
            if (p / "works-data" / "works.json").exists():
                return p

        # Try current working directory first.
        cwd = Path.cwd()
        if (cwd / "works-data" / "works.json").exists():
            return cwd

        # Ask user to select the project folder.
        chosen = filedialog.askdirectory(
            title="选择你的项目目录（包含 works-data/works.json）"
        )
        if not chosen:
            raise RuntimeError("未选择项目目录，程序退出。")

        chosen_path = Path(chosen)
        _write_json(_config_path(), {"project_dir": chosen_path.as_posix()})
        return chosen_path

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left: list
        left = ttk.Frame(self, padding=12)
        left.grid(row=0, column=0, sticky="ns")

        ttk.Label(left, text="作品列表", font=("Segoe UI", 11, "bold")).pack(
            anchor=W
        )

        self.listbox = tk.Listbox(left, width=38)
        self.listbox.pack(fill=BOTH, expand=True, pady=(8, 8))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        btn_row = ttk.Frame(left)
        btn_row.pack(fill="x")

        ttk.Button(btn_row, text="添加", command=self._on_add).pack(side=LEFT, padx=4)
        ttk.Button(btn_row, text="删除", command=self._on_delete).pack(
            side=LEFT, padx=4
        )
        self.delete_images_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            left,
            text="删除对应图片文件",
            variable=self.delete_images_var,
        ).pack(anchor=W, pady=(8, 0))

        # Right: editor
        right = ttk.Frame(self, padding=12)
        right.grid(row=0, column=1, sticky="nsew")

        editor = ttk.Frame(right)
        editor.pack(fill=BOTH, expand=True)

        # Row 0: id / image
        self.id_var = tk.StringVar(value="")
        ttk.Label(editor, text="ID").grid(row=0, column=0, sticky=W, padx=(0, 10))
        ttk.Entry(editor, textvariable=self.id_var, state="readonly").grid(
            row=0, column=1, sticky="ew"
        )

        ttk.Label(editor, text="图片").grid(row=0, column=2, sticky=W, padx=(20, 10))
        self.image_var = tk.StringVar(value="")
        ttk.Entry(editor, textvariable=self.image_var, state="readonly").grid(
            row=0, column=3, sticky="ew"
        )
        ttk.Button(editor, text="选择图片", command=self._on_pick_image).grid(
            row=0, column=4, sticky="e"
        )

        # Row 1-6: fields
        def add_entry(r, label, var):
            ttk.Label(editor, text=label).grid(row=r, column=0, sticky=W, padx=(0, 10))
            ttk.Entry(editor, textvariable=var).grid(row=r, column=1, sticky="ew", padx=(0, 10))

        def add_select(r, label, var, values):
            ttk.Label(editor, text=label).grid(row=r, column=0, sticky=W, padx=(0, 10))
            combo = ttk.Combobox(
                editor,
                textvariable=var,
                values=values,
                state="readonly",
            )
            combo.grid(row=r, column=1, sticky="ew", padx=(0, 10))
            if values and not var.get():
                var.set(values[0])

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

        add_entry(1, "标题", self.title_var)
        add_entry(2, "年份", self.year_var)
        add_select(3, "类型", self.type_var, self.field_options["type"])
        add_select(4, "系列", self.series_var, self.field_options["series"])
        add_entry(5, "媒介", self.medium_var)
        add_entry(6, "尺寸(可选)", self.size_var)
        add_select(7, "内容类型", self.content_kind_var, self.field_options["content_kind"])
        add_entry(8, "内容源src", self.content_src_var)
        add_entry(9, "封面poster(可选)", self.content_poster_var)
        add_entry(10, "网页/3D链接link(可选)", self.content_link_var)
        add_entry(11, "3D格式(modelFormat, 可选)", self.content_model_format_var)

        # Description
        ttk.Label(editor, text="文本描述").grid(
            row=12, column=0, sticky=W, padx=(0, 10), pady=(12, 0)
        )
        self.desc_text = tk.Text(editor, height=10, wrap="word")
        self.desc_text.grid(row=12, column=1, columnspan=4, sticky="nsew", pady=(12, 0))

        # Buttons
        action = ttk.Frame(right)
        action.pack(fill="x", pady=(10, 0))
        ttk.Button(action, text="保存当前作品", command=self._on_save).pack(
            side=LEFT, padx=6
        )
        ttk.Button(action, text="管理展览(exhibitions.json)", command=self._open_exhibitions_manager).pack(
            side=LEFT, padx=6
        )
        ttk.Button(action, text="刷新列表", command=self._refresh_from_disk).pack(
            side=LEFT, padx=6
        )
        ttk.Button(action, text="打开works.html提示刷新", command=self._on_hint).pack(
            side=LEFT, padx=6
        )
        ttk.Button(action, text="编辑筛选字段(filters.json)", command=self._on_edit_filters).pack(
            side=LEFT, padx=6
        )

        # Make columns expand
        for c in range(1, 5):
            editor.grid_columnconfigure(c, weight=1)
        editor.grid_rowconfigure(12, weight=1)

    def _load_works(self):
        raw = _read_json(self.works_json_path, default=[])
        if not isinstance(raw, list):
            raw = []
        self.works = [Work.from_dict(d) for d in raw if isinstance(d, dict)]

    def _save_works(self):
        _write_json(self.works_json_path, [w.to_dict() for w in self.works])

    def _refresh_list(self):
        self.listbox.delete(0, END)
        for i, w in enumerate(self.works):
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
        idx = int(sel[0])
        self.current_index = idx
        self._fill_editor(self.works[idx])

    def _fill_editor(self, w: Work):
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
        new_id = self._next_id()
        w = Work(id=new_id)
        self.works.append(w)
        self._save_works()
        self._refresh_from_disk()

        # Select the newly added item
        for i, item in enumerate(self.works):
            if item.id == new_id:
                self.listbox.selection_clear(0, END)
                self.listbox.selection_set(i)
                self.listbox.activate(i)
                self.current_index = i
                self._fill_editor(self.works[i])
                break

    def _maybe_copy_image(self, work: Work, selected_file: str) -> None:
        if not selected_file:
            return
        src = Path(selected_file)
        if not src.exists():
            return

        self.works_img_dir.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower()
        if ext == "":
            ext = ".webp"

        dest_name = f"{work.id}{ext}"
        dest_abs = self.works_img_dir / dest_name

        # Copy/overwrite image file in img/works
        shutil.copy2(src, dest_abs)

        # Store relative paths used by works.html
        rel = _to_posix_rel(self.project_dir, dest_abs)
        work.image = rel
        work.thumbnail = rel
        if not work.content_src:
            work.content_src = rel
        if not work.content_poster:
            work.content_poster = rel

    def _on_pick_image(self):
        if self.current_index is None:
            messagebox.showwarning("提示", "请先添加/选择一个作品再选择图片。")
            return
        idx = self.current_index
        w = self.works[idx]

        chosen = filedialog.askopenfilename(
            title="选择作品图片",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.gif *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not chosen:
            return

        try:
            self._maybe_copy_image(w, chosen)
            self.image_var.set(w.image)
            self.content_src_var.set(w.content_src)
            self.content_poster_var.set(w.content_poster)
        except Exception as e:
            messagebox.showerror("错误", f"复制图片失败：{e}")

    def _on_save(self):
        if self.current_index is None:
            messagebox.showwarning("提示", "请先选择或添加作品。")
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

        if w.content_kind in {"video", "audio", "image"} and not (w.content_src or w.image):
            messagebox.showwarning("提示", "当前内容类型需要 src（内容源）。")
            return
        if w.content_kind in {"web", "model"} and not (w.content_link or w.content_src):
            messagebox.showwarning("提示", "web/model 至少需要 link 或 src。")
            return

        if not w.image:
            # Keep silent? Better to warn to avoid empty modal image.
            if not messagebox.askyesno("确认", "当前作品还没有图片，保存后works.html可能无法显示。继续吗？"):
                return

        try:
            self._save_works()
            messagebox.showinfo("成功", "已保存。请刷新 works.html 查看效果。")
            self._refresh_from_disk()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")

    def _refresh_from_disk(self):
        try:
            self._load_works()
            self._refresh_list()
        except Exception as e:
            messagebox.showerror("错误", f"加载失败：{e}")

    def _on_delete(self):
        if self.current_index is None:
            messagebox.showwarning("提示", "请先选择要删除的作品。")
            return

        w = self.works[self.current_index]
        if not messagebox.askyesno("确认删除", f"确定删除《{w.title or w.id}》吗？"):
            return

        delete_images = bool(self.delete_images_var.get())
        if delete_images:
            # Delete both image and thumbnail files if they exist (they usually point to the same file).
            for rel in [w.image, w.thumbnail]:
                if not rel:
                    continue
                abs_path = self.project_dir / Path(rel)
                try:
                    if abs_path.exists():
                        abs_path.unlink()
                except Exception:
                    # Don't block deletion on file errors.
                    pass

        del self.works[self.current_index]
        try:
            self._save_works()
            self._refresh_from_disk()
            messagebox.showinfo("成功", "已删除并更新 works.json。")
        except Exception as e:
            messagebox.showerror("错误", f"删除失败：{e}")

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

        current = _read_json(self.filters_json_path, self._default_filters())
        text.insert("1.0", json.dumps(current, ensure_ascii=False, indent=2))

        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=12, pady=(0, 12))

        def on_save_filters():
            raw = text.get("1.0", END).strip()
            try:
                parsed = json.loads(raw)
                groups = parsed.get("groups", []) if isinstance(parsed, dict) else []
                if not isinstance(groups, list):
                    raise ValueError("groups 必须是数组")
                _write_json(self.filters_json_path, parsed)
                messagebox.showinfo("成功", "筛选配置已保存。刷新 works.html 即可生效。")
                win.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"filters.json 格式不正确：{e}")

        def on_format_json():
            try:
                parsed = json.loads(text.get("1.0", END).strip())
                text.delete("1.0", END)
                text.insert("1.0", json.dumps(parsed, ensure_ascii=False, indent=2))
            except Exception as e:
                messagebox.showerror("错误", f"无法格式化：{e}")

        ttk.Button(btns, text="格式化JSON", command=on_format_json).pack(side=LEFT, padx=4)
        ttk.Button(btns, text="保存配置", command=on_save_filters).pack(side=LEFT, padx=4)

    def _on_hint(self):
        messagebox.showinfo(
            "提示",
            "works.html 依赖 js/works.js 动态读取 works-data/works.json。\n"
            "保存/删除后请刷新 works.html 查看列表变化。",
        )


def main():
    app = WorksManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()

