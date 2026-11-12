
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image
import numpy as np
import cv2
import random
import math
import time

class RGBReconstructionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RGB Color Reconstruction")
        self.root.geometry("480x370")

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.order = tk.StringVar(value="random")
        self.duration = tk.StringVar(value="40")
        self.hold = tk.StringVar(value="5")
        self.status = tk.StringVar(value="BMPを選択してください")

        frame = ttk.Frame(root, padding=15)
        frame.pack(fill="both", expand=True)

        ttk.Button(
            frame, text="BMPを選択",
            command=self.select_input
        ).pack(fill="x", pady=5)

        ttk.Label(
            frame, textvariable=self.input_path,
            wraplength=440
        ).pack()

        ttk.Label(
            frame, text="色の出現順序"
        ).pack(pady=(15, 5))

        ttk.Radiobutton(
            frame, text="ランダムに1色ずつ",
            variable=self.order, value="random"
        ).pack(anchor="w")

        ttk.Radiobutton(
            frame, text="暗い色から1色ずつ",
            variable=self.order, value="dark"
        ).pack(anchor="w")

        ttk.Label(
            frame, text="復元時間（秒）"
        ).pack(pady=(12, 0))
        ttk.Entry(
            frame, textvariable=self.duration
        ).pack(fill="x")

        ttk.Label(
            frame, text="完成後の静止時間（秒）"
        ).pack(pady=(8, 0))
        ttk.Entry(
            frame, textvariable=self.hold
        ).pack(fill="x")

        ttk.Button(
            frame, text="MP4動画を作成",
            command=self.create_video
        ).pack(fill="x", pady=15)

        ttk.Label(
            frame, textvariable=self.status,
            wraplength=440
        ).pack()

    def select_input(self):
        path = filedialog.askopenfilename(
            title="BMP画像を選択",
            filetypes=[("BMP", "*.bmp")]
        )
        if path:
            self.input_path.set(path)

    def create_video(self):
        path = self.input_path.get()
        if not path:
            self.status.set("BMPを選択してください")
            return

        try:
            duration = float(self.duration.get())
            hold = float(self.hold.get())
            if duration <= 0 or hold < 0:
                raise ValueError
        except ValueError:
            self.status.set("時間の設定を確認してください")
            return

        output = filedialog.asksaveasfilename(
            title="MP4保存先",
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4")]
        )
        if not output:
            return

        self.status.set("画像を解析しています...")
        self.root.update_idletasks()

        try:
            with Image.open(path) as img:
                rgb = np.array(img.convert("RGB"))

            height, width = rgb.shape[:2]
            pixels = rgb.reshape(-1, 3)

            colors, inverse, counts = np.unique(
                pixels, axis=0,
                return_inverse=True,
                return_counts=True
            )

            color_count = len(colors)
            print(f"画像サイズ: {width} x {height}")
            print(f"異なるRGB色数: {color_count:,}")

            indices = list(range(color_count))

            if self.order.get() == "random":
                random.shuffle(indices)
            else:
                brightness = (
                    colors[:, 0].astype(float) * 0.2126
                    + colors[:, 1].astype(float) * 0.7152
                    + colors[:, 2].astype(float) * 0.0722
                )
                indices = np.argsort(
                    brightness, kind="stable"
                ).tolist()

            # 色ごとのピクセル位置を高速に取り出す
            sorted_pixels = np.argsort(
                inverse, kind="stable"
            )
            offsets = np.zeros(
                color_count + 1, dtype=np.int64
            )
            offsets[1:] = np.cumsum(counts)

            fps = 30
            total_frames = max(1, math.ceil(duration * fps))
            hold_frames = math.ceil(hold * fps)

            # OpenCVはBGR形式
            original_bgr = cv2.cvtColor(
                rgb, cv2.COLOR_RGB2BGR
            )

            # MP4のため偶数サイズにする
            out_width = width + width % 2
            out_height = height + height % 2

            def fit_frame(frame):
                if out_width == width and out_height == height:
                    return frame
                return cv2.copyMakeBorder(
                    frame, 0, out_height - height,
                    0, out_width - width,
                    cv2.BORDER_CONSTANT,
                    value=(0, 0, 0)
                )

            writer = cv2.VideoWriter(
                output,
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps,
                (out_width, out_height)
            )

            if not writer.isOpened():
                raise RuntimeError("MP4を作成できません")

            canvas = np.zeros_like(original_bgr)
            canvas_flat = canvas.reshape(-1, 3)

            next_color = 0
            start = time.time()

            try:
                for frame_no in range(total_frames):
                    # 最終フレームで全色が揃う
                    target = math.floor(
                        (frame_no + 1)
                        * color_count / total_frames
                    )

                    while next_color < target:
                        color_id = indices[next_color]

                        a = offsets[color_id]
                        b = offsets[color_id + 1]
                        positions = sorted_pixels[a:b]

                        canvas_flat[positions] = (
                            colors[color_id][::-1]
                        )
                        next_color += 1

                    writer.write(fit_frame(canvas))

                    if frame_no % 30 == 0:
                        self.status.set(
                            f"処理中: {frame_no + 1}"
                            f"/{total_frames} フレーム"
                        )
                        self.root.update_idletasks()

                # 最後は必ず元画像を表示
                final_frame = fit_frame(original_bgr)
                for _ in range(hold_frames):
                    writer.write(final_frame)

            finally:
                writer.release()

            elapsed = time.time() - start

            self.status.set("動画作成完了！")
            print("動画作成完了！")
            print(f"保存先: {output}")
            print(f"色数: {color_count:,}")
            print(f"処理時間: {elapsed:.1f}秒")

        except Exception as e:
            self.status.set(f"エラー: {e}")
            print("エラー:", e)


root = tk.Tk()
app = RGBReconstructionApp(root)
root.mainloop()
