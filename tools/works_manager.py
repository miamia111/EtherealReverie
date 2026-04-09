import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
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

    @staticmethod
    def from_dict(d: dict) -> "Work":
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
        }


class WorksManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Works Manager (works-data/works.json)")
        self.geometry("980x620")

        self.project_dir = self._resolve_project_dir()
        self.works_json_path = self.project_dir / "works-data" / "works.json"
        self.works_img_dir = self.project_dir / "img" / "works"

        self.works: List[Work] = []
        self.current_index: Optional[int] = None

        self._build_ui()
        self._load_works()
        self._refresh_list()

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

        self.title_var = tk.StringVar(value="")
        self.year_var = tk.StringVar(value="")
        self.type_var = tk.StringVar(value="")
        self.series_var = tk.StringVar(value="")
        self.medium_var = tk.StringVar(value="")
        self.size_var = tk.StringVar(value="")

        add_entry(1, "标题", self.title_var)
        add_entry(2, "年份", self.year_var)
        add_entry(3, "类型", self.type_var)
        add_entry(4, "系列", self.series_var)
        add_entry(5, "媒介", self.medium_var)
        add_entry(6, "尺寸(可选)", self.size_var)

        # Description
        ttk.Label(editor, text="文本描述").grid(
            row=7, column=0, sticky=W, padx=(0, 10), pady=(12, 0)
        )
        self.desc_text = tk.Text(editor, height=10, wrap="word")
        self.desc_text.grid(row=7, column=1, columnspan=4, sticky="nsew", pady=(12, 0))

        # Buttons
        action = ttk.Frame(right)
        action.pack(fill="x", pady=(10, 0))
        ttk.Button(action, text="保存当前作品", command=self._on_save).pack(
            side=LEFT, padx=6
        )
        ttk.Button(action, text="刷新列表", command=self._refresh_from_disk).pack(
            side=LEFT, padx=6
        )
        ttk.Button(action, text="打开works.html提示刷新", command=self._on_hint).pack(
            side=LEFT, padx=6
        )

        # Make columns expand
        for c in range(1, 5):
            editor.grid_columnconfigure(c, weight=1)
        editor.grid_rowconfigure(7, weight=1)

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

