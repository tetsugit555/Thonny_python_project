
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image
import numpy as np
import cv2
import math
import time

class DifferenceScanApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RGB Difference Scan")
        self.root.geometry("520x430")

        self.path_a = tk.StringVar()
        self.path_b = tk.StringVar()
        self.duration = tk.StringVar(value="30")
        self.intro = tk.StringVar(value="5")
        self.hold = tk.StringVar(value="5")
        self.status = tk.StringVar(value="BMPを2枚選択してください")

        frame = ttk.Frame(root, padding=15)
        frame.pack(fill="both", expand=True)

        ttk.Button(
            frame, text="画像Aを選択（最初に表示）",
            command=lambda: self.choose(self.path_a)
        ).pack(fill="x", pady=5)

        ttk.Label(
            frame, textvariable=self.path_a,
            wraplength=470
        ).pack()

        ttk.Button(
            frame, text="画像Bを選択（差分計算用）",
            command=lambda: self.choose(self.path_b)
        ).pack(fill="x", pady=5)

        ttk.Label(
            frame, textvariable=self.path_b,
            wraplength=470
        ).pack()

        for label, variable in [
            ("書き換え時間（秒）", self.duration),
            ("最初の画像Aの表示時間（秒）", self.intro),
            ("完成後の静止時間（秒）", self.hold)
        ]:
            ttk.Label(frame, text=label).pack(pady=(10, 0))
            ttk.Entry(
                frame, textvariable=variable
            ).pack(fill="x")

        ttk.Button(
            frame, text="MP4動画を作成",
            command=self.create_video
        ).pack(fill="x", pady=15)

        ttk.Label(
            frame, textvariable=self.status,
            wraplength=470
        ).pack()

    def choose(self, variable):
        path = filedialog.askopenfilename(
            title="BMP画像を選択",
            filetypes=[("BMP画像", "*.bmp")]
        )
        if path:
            variable.set(path)

    def create_video(self):
        if not self.path_a.get() or not self.path_b.get():
            self.status.set("BMPを2枚選択してください")
            return

        try:
            duration = float(self.duration.get())
            intro = float(self.intro.get())
            hold = float(self.hold.get())

            if duration <= 0 or intro < 0 or hold < 0:
                raise ValueError

        except ValueError:
            self.status.set("時間の設定を確認してください")
            return

        output = filedialog.asksaveasfilename(
            title="MP4の保存先",
            defaultextension=".mp4",
            filetypes=[("MP4動画", "*.mp4")]
        )
        if not output:
            return

        writer = None

        try:
            self.status.set("BMPを読み込んでいます...")
            self.root.update_idletasks()

            with Image.open(self.path_a.get()) as img:
                a = np.array(img.convert("RGB"))

            with Image.open(self.path_b.get()) as img:
                b = np.array(img.convert("RGB"))

            if a.shape != b.shape:
                raise ValueError(
                    "2枚の画像の縦横サイズが違います"
                )

            height, width = a.shape[:2]

            # オーバーフローを防いで絶対差分を計算
            diff = np.abs(
                a.astype(np.int16) - b.astype(np.int16)
            ).astype(np.uint8)

            original = cv2.cvtColor(
                a, cv2.COLOR_RGB2BGR
            )
            difference = cv2.cvtColor(
                diff, cv2.COLOR_RGB2BGR
            )

            fps = 30
            intro_frames = round(intro * fps)
            scan_frames = max(1, math.ceil(duration * fps))
            hold_frames = round(hold * fps)

            # 各横行にランダムな開始時刻と速度を割り当てる
            rng = np.random.default_rng()

            start_times = rng.uniform(
                0, duration * 0.55, size=height
            )

            # 遅く始まる行も最後まで到達するよう調整
            available = duration - start_times

            # 行ごとにランダムな所要時間
            travel_times = available * rng.uniform(
                0.45, 1.0, size=height
            )

            # 動画の縦横を偶数にする
            out_width = width + width % 2
            out_height = height + height % 2

            def fit_frame(frame):
                if (out_width == width
                        and out_height == height):
                    return frame
                return cv2.copyMakeBorder(
                    frame,
                    0, out_height - height,
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
                raise RuntimeError(
                    "MP4ファイルを作成できません"
                )

            start = time.time()

            # まず画像Aを静止表示
            first_frame = fit_frame(original)
            for _ in range(intro_frames):
                writer.write(first_frame)

            # 作業用画像
            canvas = original.copy()
            rows = np.arange(height)

            # 各行の現在の書き換え位置
            previous_x = np.zeros(
                height, dtype=np.int32
            )

            for frame_no in range(scan_frames):
                t = min(
                    duration,
                    (frame_no + 1) / scan_frames * duration
                )

                progress = np.clip(
                    (t - start_times) / travel_times,
                    0.0, 1.0
                )

                current_x = np.floor(
                    progress * width
                ).astype(np.int32)

                # 伸びた部分だけ差分画像に書き換える
                changed = np.where(
                    current_x > previous_x
                )[0]

                for y in changed:
                    x0 = previous_x[y]
                    x1 = current_x[y]

                    canvas[y, x0:x1] = difference[y, x0:x1]

                previous_x = current_x

                writer.write(fit_frame(canvas))

                if frame_no % 30 == 0:
                    self.status.set(
                        f"書き換え中: "
                        f"{frame_no + 1}/{scan_frames}"
                    )
                    self.root.update_idletasks()

            # 最後に差分画像を完全表示
            final_frame = fit_frame(difference)
            for _ in range(hold_frames):
                writer.write(final_frame)

            elapsed = time.time() - start

            self.status.set("動画作成完了！")
            print("動画作成完了！")
            print(f"画像サイズ: {width} x {height}")
            print(f"保存先: {output}")
            print(f"処理時間: {elapsed:.1f}秒")

        except Exception as e:
            self.status.set(f"エラー: {e}")
            print("エラー:", e)

        finally:
            if writer is not None:
                writer.release()


root = tk.Tk()
app = DifferenceScanApp(root)
root.mainloop()
