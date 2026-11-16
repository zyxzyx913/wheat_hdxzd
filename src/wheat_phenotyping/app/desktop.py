"""单图和文件夹批量 RGB 植被识别桌面入口。"""

from __future__ import annotations

import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from wheat_phenotyping.app.inference import ALGORITHM_NAMES, discover_images, run_image_batch
from wheat_phenotyping.data import load_rgb_image


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULTS_PATH = PROJECT_ROOT / "configs" / "segmentation" / "desktop_frozen_defaults.json"
MODEL_PATH = PROJECT_ROOT / "results" / "ews" / "rf_training" / "rf_color_texture.joblib"


class WheatAnalysisApp:
    """为单张或文件夹图像提供算法选择、批量推理和结果查看。"""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("小麦图像植被识别")
        self.root.geometry("1180x820")
        self.input_path: Path | None = None
        self.output_path: Path | None = None
        self.preview_refs: dict[str, ImageTk.PhotoImage] = {}
        self.method = tk.StringVar(value="全部算法")
        self.recursive = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="选择一张图像或文件夹开始分析。")
        self._build()

    def _build(self) -> None:
        header = ttk.Frame(self.root, padding=12)
        header.pack(fill="x")
        ttk.Label(header, text="小麦图像植被识别", font=("Microsoft YaHei UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="识别目标为活体植被与非活体/背景；不区分叶、茎、穗，也不预测农学长势。",
            foreground="#9a4d00",
        ).pack(anchor="w", pady=(3, 10))
        controls = ttk.Frame(header)
        controls.pack(fill="x")
        ttk.Button(controls, text="选择单张图片", command=self.choose_image).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="选择文件夹", command=self.choose_folder).pack(side="left", padx=6)
        ttk.Label(controls, text="算法：").pack(side="left", padx=(12, 4))
        ttk.Combobox(
            controls, textvariable=self.method,
            values=("全部算法", *ALGORITHM_NAMES), state="readonly", width=22,
        ).pack(side="left")
        ttk.Checkbutton(controls, text="包含子文件夹", variable=self.recursive).pack(side="left", padx=8)
        ttk.Button(controls, text="结果保存位置", command=self.choose_output).pack(side="left", padx=6)
        ttk.Button(controls, text="开始分析", command=self.analyze).pack(side="left", padx=6)
        self.input_label = ttk.Label(header, text="输入：尚未选择", wraplength=1100)
        self.input_label.pack(anchor="w", pady=(8, 2))
        self.output_label = ttk.Label(header, text="输出：自动创建独立结果文件夹", wraplength=1100)
        self.output_label.pack(anchor="w")

        body = ttk.Panedwindow(self.root, orient="vertical")
        body.pack(fill="both", expand=True, padx=12, pady=6)
        top = ttk.Frame(body)
        bottom = ttk.Frame(body)
        body.add(top, weight=3)
        body.add(bottom, weight=2)
        preview = ttk.Frame(top)
        preview.pack(fill="both", expand=True)
        self.original_panel = self._panel(preview, "原图")
        self.mask_panel = self._panel(preview, "植被掩膜")
        self.overlay_panel = self._panel(preview, "分割叠加")
        for panel in (self.original_panel, self.mask_panel, self.overlay_panel):
            panel.pack(side="left", fill="both", expand=True, padx=4)

        columns = ("image", "algorithm", "status", "area", "runtime", "error")
        self.table = ttk.Treeview(bottom, columns=columns, show="headings", height=11)
        headings = {"image": "图像", "algorithm": "算法", "status": "状态", "area": "植被占比", "runtime": "耗时(秒)", "error": "错误"}
        widths = {"image": 220, "algorithm": 150, "status": 70, "area": 90, "runtime": 90, "error": 390}
        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=widths[column], anchor="w")
        scrollbar = ttk.Scrollbar(bottom, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        ttk.Label(self.root, textvariable=self.status, padding=10).pack(fill="x")

    @staticmethod
    def _panel(parent: ttk.Frame, title: str) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(parent, text=title, padding=6)
        ttk.Label(frame, text="等待图像", anchor="center").pack(fill="both", expand=True)
        return frame

    def _show(self, panel: ttk.LabelFrame, image: Image.Image) -> None:
        for child in panel.winfo_children():
            child.destroy()
        preview = image.copy()
        preview.thumbnail((350, 360))
        photo = ImageTk.PhotoImage(preview)
        self.preview_refs[panel.winfo_name() + str(id(panel))] = photo
        ttk.Label(panel, image=photo, anchor="center").pack(fill="both", expand=True)

    def choose_image(self) -> None:
        selected = filedialog.askopenfilename(
            title="选择小麦 RGB 图像",
            filetypes=(("图像文件", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.ppm"), ("所有文件", "*.*")),
        )
        if selected:
            self.input_path = Path(selected)
            self.input_label.configure(text=f"输入：{self.input_path}")
            try:
                image = load_rgb_image(self.input_path)
                self._show(self.original_panel, Image.frombytes("RGB", (image.width, image.height), image.pixels))
            except Exception as error:
                messagebox.showerror("图像读取失败", str(error))

    def choose_folder(self) -> None:
        selected = filedialog.askdirectory(title="选择包含 RGB 图像的文件夹")
        if selected:
            self.input_path = Path(selected)
            self.input_label.configure(text=f"输入文件夹：{self.input_path}")
            self.status.set("已选择文件夹；是否递归读取子文件夹由复选框控制。")

    def choose_output(self) -> None:
        selected = filedialog.askdirectory(title="选择批量分析结果的父文件夹")
        if selected:
            self.output_path = Path(selected)
            self.output_label.configure(text=f"输出父文件夹：{self.output_path}")

    def _read_defaults(self) -> dict[str, object]:
        config = json.loads(DEFAULTS_PATH.read_text(encoding="utf-8"))
        if not isinstance(config.get("algorithm_parameters"), dict):
            raise ValueError("桌面端冻结参数配置缺少 algorithm_parameters")
        return config

    def analyze(self) -> None:
        if self.input_path is None:
            messagebox.showinfo("需要输入", "请先选择一张图片或一个文件夹。")
            return
        try:
            paths = discover_images(self.input_path, recursive=self.recursive.get())
            if not paths:
                messagebox.showinfo("没有图像", "所选位置没有支持格式的图像文件。")
                return
            config = self._read_defaults()
            methods = list(ALGORITHM_NAMES) if self.method.get() == "全部算法" else [self.method.get()]
            output_parent = self.output_path or (PROJECT_ROOT / "results" / "image_inference")
            output_dir = output_parent / datetime.now().strftime("run_%Y%m%d_%H%M%S_%f")
            self.status.set(f"开始分析：{len(paths)} 张图像 × {len(methods)} 种算法。")
            self.root.update_idletasks()

            def update_progress(done: int, total: int, label: str) -> None:
                self.status.set(f"处理中 {done}/{total}：{label}")
                self.root.update_idletasks()

            rows = run_image_batch(
                paths, methods, output_dir,
                model= None,
                model_path=MODEL_PATH,
                algorithm_parameters=config["algorithm_parameters"],
                rf_probability_threshold=float(config.get("rf_probability_threshold", 0.75)),
                source_root=self.input_path if self.input_path.is_dir() else None,
                progress=update_progress,
            )
            for item in self.table.get_children():
                self.table.delete(item)
            for row in rows:
                self.table.insert("", "end", values=(
                    Path(str(row["image_path"])).name, row["algorithm"], row["status"],
                    "" if row["green_area_fraction"] is None else f"{float(row['green_area_fraction']):.2%}",
                    "" if row["runtime_seconds"] is None else f"{float(row['runtime_seconds']):.3f}", row["error"],
                ))
            first_success = next((row for row in rows if row["status"] == "ok"), None)
            if first_success:
                source_image = load_rgb_image(first_success["image_path"])
                mask_image = Image.open(first_success["mask_path"]).convert("L")
                overlay_image = Image.open(first_success["overlay_path"]).convert("RGB")
                self._show(self.original_panel, Image.frombytes("RGB", (source_image.width, source_image.height), source_image.pixels))
                self._show(self.mask_panel, mask_image)
                self._show(self.overlay_panel, overlay_image)
            failures = sum(row["status"] != "ok" for row in rows)
            self.output_label.configure(text=f"结果目录：{output_dir}")
            self.status.set(f"完成：{len(paths)} 张图像，{len(rows)} 条算法结果，失败 {failures} 条。CSV、JSON、掩膜和叠加图已保存。")
        except Exception as error:
            messagebox.showerror("分析失败", str(error))
            self.status.set("分析未完成；请查看错误信息并检查输入、参数配置及模型文件。")


def main() -> None:
    """启动 Windows Tk 桌面界面。"""
    root = tk.Tk()
    WheatAnalysisApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
