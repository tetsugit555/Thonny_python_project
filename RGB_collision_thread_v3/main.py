"""RGB Stripe & Grid — モジュール版。起動: python main.py"""
import tkinter as tk
import queue
import threading
from tkinter import ttk, filedialog
import cv2

#おそらく同じフォルダのモジュールの呼び出し
from text_renderer import TextRendererMixin
from stripe_motion import StripeMotionMixin
from rgb_stream import RGBStreamMixin
from rgb_collision import RGBCollisionMixin
from video_export import VideoExportMixin
from video_renderer import VideoRendererMixin

class StripeGridApp(TextRendererMixin, StripeMotionMixin, RGBStreamMixin, RGBCollisionMixin, VideoExportMixin, VideoRendererMixin):
    FPS = 30
    FONT = cv2.FONT_HERSHEY_SIMPLEX

    def __init__(self, root):
        self.root = root
        self._ui_queue = queue.Queue()
        self._main_thread_id = threading.get_ident()
        self._worker_data_format = "hex"
        root.after(100, self._poll_ui_queue)
        root.title("RGB Data Collision Ver. 3")
        root.geometry("610x820")

        self.path = tk.StringVar()
        self.intro_time = tk.StringVar(value="3")
        self.horizontal_time = tk.StringVar(value="20")
        self.vertical_time = tk.StringVar(value="20")
        self.grid_time = tk.DoubleVar(value=40)
        self.pause_time = tk.StringVar(value="2")
        self.final_time = tk.StringVar(value="5")

        self.data_format = tk.StringVar(value="hex")
         #v5 で追加
        self.output_mode = tk.StringVar(value="normal")
        self.max_events = tk.StringVar(value="6")
        self.stream_count = tk.StringVar(value="18")

        self.brightness = tk.DoubleVar(value=55)
        self.speed_percent = tk.DoubleVar(value=100)
        self.freeze_seconds = tk.DoubleVar(value=5)
        self.post_grid_motion_seconds = tk.DoubleVar(value=30)

        self.status = tk.StringVar(
            value="BMPを選択してください"
        )

        self.base_scale = 0.5
        self.image_height = 1080

        outer = ttk.Frame(root)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            outer, highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            outer, orient="vertical",
            command=canvas.yview
        )
        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        frame = ttk.Frame(canvas, padding=15)
        window_id = canvas.create_window(
            (0, 0), window=frame, anchor="nw"
        )

        frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfigure(
                window_id, width=e.width
            )
        )

        ttk.Button(
            frame, text="BMP画像を選択",
            command=self.choose_image
        ).pack(fill="x", pady=5)

        ttk.Label(
            frame, textvariable=self.path,
            wraplength=540
        ).pack()

        settings = [
            ("元画像の表示時間（秒）", self.intro_time),
            ("横ストライプ変換時間（秒）", self.horizontal_time),
            ("縦ストライプ変換時間（秒）", self.vertical_time),
            ("ストライプ完成後の静止時間（秒）", self.pause_time),
            ("最後のグリッド単独表示（秒）", self.final_time),
            ("同時RGB融合イベント最大数", self.max_events),
            ("背景RGBデータ列の数", self.stream_count)
        ]

        for label, variable in settings:
            ttk.Label(
                frame, text=label
            ).pack(pady=(6, 0))
            ttk.Entry(
                frame, textvariable=variable
            ).pack(fill="x")

        ttk.Label(
            frame, text="RGBデータ表示形式"
        ).pack(pady=(12, 4))

        ttk.Radiobutton(
            frame, text="通常 (R, G, B)",
            variable=self.data_format,
            value="rgb"
        ).pack(anchor="w")

        ttk.Radiobutton(
            frame, text="16進数 #RRGGBB",
            variable=self.data_format,
            value="hex"
        ).pack(anchor="w")

        self.add_slider(
            frame,
            "背景RGB文字の明るさ",
            self.brightness,
            0, 100, "%"
        )

        self.add_slider(
            frame,
            "背景RGBデータの速度倍率",
            self.speed_percent,
            10, 300, "%"
        )

        self.add_slider(
            frame,
            "グリッド生成時間",
            self.grid_time,
            5, 180, "秒"
        )

        self.add_slider(
            frame,
            "グリッド完成後・RGBデータが飛び交う時間",
            self.post_grid_motion_seconds,
            0, 180, "秒"
        )

        self.add_slider(
            frame,
            "完成後のRGBデータ静止時間",
            self.freeze_seconds,
            0, 30, "秒"
        )

        # v5 で追加
        ttk.Label(
            frame, text="動画の出力形式"
        ).pack(pady=(15, 4))

        ttk.Radiobutton(
        frame,
        text="通常（元画像サイズ・MP4）",
        variable=self.output_mode,
        value="normal"
        ).pack(anchor="w")

        ttk.Radiobutton(
            frame,
            text="Instagram用（1080×1920・H.264）",
            variable=self.output_mode,
            value="instagram"
        ).pack(anchor="w")

        self.start_button = ttk.Button(
            frame,
            text="MP4動画を作成",
            command=self.create_video
        )
        self.start_button.pack(fill="x", pady=15)

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 8))

        ttk.Label(
            frame,
            textvariable=self.status,
            wraplength=540
        ).pack()

    def add_slider(
        self, parent, title, variable,
        minimum, maximum, unit
    ):
        ttk.Label(
            parent, text=title
        ).pack(pady=(12, 2))

        value_label = ttk.Label(
            parent, text=f"{variable.get():.0f}{unit}"
        )
        value_label.pack()

        ttk.Scale(
            parent,
            from_=minimum,
            to=maximum,
            variable=variable,
            command=lambda v: value_label.config(
                text=f"{float(v):.0f}{unit}"
            )
        ).pack(fill="x")

    def choose_image(self):
        path = filedialog.askopenfilename(
            title="BMP画像を選択",
            filetypes=[("BMP画像", "*.bmp")]
        )
        if path:
            self.path.set(path)

    def update_status(self, message):
        if threading.get_ident() != self._main_thread_id:
            self._ui_queue.put(("status", message))
        else:
            self.status.set(message)

    def _poll_ui_queue(self):
        try:
            while True:
                kind, value = self._ui_queue.get_nowait()
                if kind == "status":
                    self.status.set(value)
                elif kind == "finished":
                    self.progress.stop()
                    self.start_button.config(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_ui_queue)

    def rgb_text(self, color):
        # 既存Mixinのrgb_text()と同じ文字形式。ワーカーではTk変数を読まない。
        r, g, b = [int(v) for v in color]
        if self._worker_data_format == "hex":
            return f"#{r:02X}{g:02X}{b:02X}"
        return f"({r},{g},{b})"


if __name__ == "__main__":
    root = tk.Tk()
    app = StripeGridApp(root)
    root.mainloop()
