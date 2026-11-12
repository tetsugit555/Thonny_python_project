
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image
import numpy as np
import cv2
import math
import time


class StripeGridApp:

    def __init__(self, root):
        self.root = root
        root.title("RGB Stripe & Grid Transformation")
        root.geometry("540x540")

        self.path = tk.StringVar()
        self.horizontal_time = tk.StringVar(value="20")
        self.vertical_time = tk.StringVar(value="20")
        self.grid_time = tk.StringVar(value="30")
        self.pause_time = tk.StringVar(value="2")
        self.final_time = tk.StringVar(value="5")
        self.status = tk.StringVar(value="BMPを選択してください")

        frame = ttk.Frame(root, padding=15)
        frame.pack(fill="both", expand=True)

        ttk.Button(
            frame, text="BMP画像を選択",
            command=self.choose_image
        ).pack(fill="x", pady=5)

        ttk.Label(
            frame, textvariable=self.path,
            wraplength=500
        ).pack()

        settings = [
            ("横ストライプ変換時間（秒）",
             self.horizontal_time),
            ("縦ストライプ変換時間（秒）",
             self.vertical_time),
            ("グリッド変換時間（秒）",
             self.grid_time),
            ("各ストライプ完成後の静止時間（秒）",
             self.pause_time),
            ("グリッド完成後の静止時間（秒）",
             self.final_time)
        ]

        for label, variable in settings:
            ttk.Label(
                frame, text=label
            ).pack(pady=(9, 0))

            ttk.Entry(
                frame, textvariable=variable
            ).pack(fill="x")

        self.start_button = ttk.Button(
            frame,
            text="MP4動画を作成",
            command=self.create_video
        )
        self.start_button.pack(fill="x", pady=15)

        ttk.Label(
            frame, textvariable=self.status,
            wraplength=500
        ).pack()

    def choose_image(self):
        path = filedialog.askopenfilename(
            title="BMP画像を選択",
            filetypes=[("BMP画像", "*.bmp")]
        )
        if path:
            self.path.set(path)

    def update_status(self, message):
        self.status.set(message)
        self.root.update_idletasks()

    # 各行・列の開始時刻と移動速度をランダム化
    def make_motion(self, count, duration, rng):
        starts = rng.uniform(
            0, duration * 0.55, size=count
        )

        remaining = duration - starts

        travel = remaining * rng.uniform(
            0.45, 1.0, size=count
        )

        return starts, travel

    def get_positions(
        self, t, starts, travel, length
    ):
        progress = np.clip(
            (t - starts) / travel, 0, 1
        )
        return np.floor(
            progress * length
        ).astype(np.int32)

    def create_video(self):
        if not self.path.get():
            self.update_status("BMPを選択してください")
            return

        try:
            h_time = float(self.horizontal_time.get())
            v_time = float(self.vertical_time.get())
            g_time = float(self.grid_time.get())
            pause = float(self.pause_time.get())
            final = float(self.final_time.get())

            if min(h_time, v_time, g_time) <= 0:
                raise ValueError

            if min(pause, final) < 0:
                raise ValueError

        except ValueError:
            self.update_status("時間設定を確認してください")
            return

        output = filedialog.asksaveasfilename(
            title="MP4保存先",
            defaultextension=".mp4",
            filetypes=[("MP4動画", "*.mp4")]
        )
        if not output:
            return

        writer = None
        self.start_button.config(state="disabled")

        try:
            start_clock = time.time()

            self.update_status("BMPを解析中...")

            with Image.open(self.path.get()) as img:
                rgb = np.array(img.convert("RGB"))

            height, width = rgb.shape[:2]

            # 行ごとの平均RGB
            row_colors = np.rint(
                rgb.mean(axis=1)
            ).astype(np.uint8)

            # 列ごとの平均RGB
            col_colors = np.rint(
                rgb.mean(axis=0)
            ).astype(np.uint8)

            # 横ストライプ画像
            horizontal = np.broadcast_to(
                row_colors[:, None, :],
                rgb.shape
            ).copy()

            # 縦ストライプ画像
            vertical = np.broadcast_to(
                col_colors[None, :, :],
                rgb.shape
            ).copy()

            # 横・縦ストライプの絶対差分
            grid = np.abs(
                horizontal.astype(np.int16)
                - vertical.astype(np.int16)
            ).astype(np.uint8)

            # OpenCV用のBGRに変換
            original = cv2.cvtColor(
                rgb, cv2.COLOR_RGB2BGR
            )
            horizontal = cv2.cvtColor(
                horizontal, cv2.COLOR_RGB2BGR
            )
            vertical = cv2.cvtColor(
                vertical, cv2.COLOR_RGB2BGR
            )
            grid = cv2.cvtColor(
                grid, cv2.COLOR_RGB2BGR
            )

            fps = 30

            out_w = width + width % 2
            out_h = height + height % 2

            def fit_frame(frame):
                if out_w == width and out_h == height:
                    return frame

                return cv2.copyMakeBorder(
                    frame,
                    0, out_h - height,
                    0, out_w - width,
                    cv2.BORDER_CONSTANT,
                    value=(0, 0, 0)
                )

            writer = cv2.VideoWriter(
                output,
                cv2.VideoWriter_fourcc(*"mp4v"),
                fps,
                (out_w, out_h)
            )

            if not writer.isOpened():
                raise RuntimeError(
                    "MP4を作成できません"
                )

            rng = np.random.default_rng()

            def write(frame):
                writer.write(fit_frame(frame))

            def hold(frame, seconds):
                for _ in range(round(seconds * fps)):
                    write(frame)

            def scan(
                base, target, duration, axis, title
            ):
                canvas = base.copy()

                count = height if axis == "row" else width
                length = width if axis == "row" else height

                starts, travel = self.make_motion(
                    count, duration, rng
                )

                previous = np.zeros(
                    count, dtype=np.int32
                )

                frames = max(1, math.ceil(duration * fps))

                for f in range(frames):
                    t = duration * (f + 1) / frames

                    positions = self.get_positions(
                        t, starts, travel, length
                    )

                    changed = np.flatnonzero(
                        positions > previous
                    )

                    for index in changed:
                        p0 = previous[index]
                        p1 = positions[index]

                        if axis == "row":
                            canvas[index, p0:p1] = (
                                target[index, p0:p1]
                            )
                        else:
                            canvas[p0:p1, index] = (
                                target[p0:p1, index]
                            )

                    previous = positions
                    write(canvas)

                    if f % 30 == 0:
                        self.update_status(
                            f"{title}: {f+1}/{frames}"
                        )

                return target.copy()

            # ---------------------------------
            # 1. 写真から横ストライプへ
            # ---------------------------------
            canvas = scan(
                original, horizontal,
                h_time, "row",
                "横ストライプ変換"
            )

            hold(canvas, pause)

            # ---------------------------------
            # 2. 横から縦ストライプへ
            # ---------------------------------
            canvas = scan(
                canvas, vertical,
                v_time, "col",
                "縦ストライプ変換"
            )

            hold(canvas, pause)

            # ---------------------------------
            # 3. 横線と縦線が同時に進む
            # 交差したピクセルだけ差分色にする
            # ---------------------------------
            self.update_status("グリッド変換中...")

            canvas = vertical.copy()

            row_starts, row_travel = self.make_motion(
                height, g_time, rng
            )
            col_starts, col_travel = self.make_motion(
                width, g_time, rng
            )

            row_previous = np.zeros(
                height, dtype=np.int32
            )
            col_previous = np.zeros(
                width, dtype=np.int32
            )

            # 各ピクセルに横線・縦線が到達したか
            row_passed = np.zeros(
                (height, width), dtype=bool
            )
            col_passed = np.zeros(
                (height, width), dtype=bool
            )

            frames = max(1, math.ceil(g_time * fps))

            for f in range(frames):
                t = g_time * (f + 1) / frames

                row_x = self.get_positions(
                    t, row_starts, row_travel, width
                )
                col_y = self.get_positions(
                    t, col_starts, col_travel, height
                )

                # 左端から横線が伸びる
                for y in np.flatnonzero(
                    row_x > row_previous
                ):
                    row_passed[
                        y, row_previous[y]:row_x[y]
                    ] = True

                # 上端から縦線が伸びる
                for x in np.flatnonzero(
                    col_y > col_previous
                ):
                    col_passed[
                        col_previous[x]:col_y[x], x
                    ] = True

                # 両方の線が通過した部分だけ変換
                intersection = row_passed & col_passed

                canvas[intersection] = grid[intersection]

                row_previous = row_x
                col_previous = col_y

                write(canvas)

                if f % 30 == 0:
                    self.update_status(
                        f"グリッド変換: {f+1}/{frames}"
                    )

            # 最後は必ず完成グリッドを表示
            hold(grid, final)

            elapsed = time.time() - start_clock

            self.update_status("動画作成完了！")

            print("動画作成完了！")
            print(f"画像サイズ: {width} x {height}")
            print(f"動画保存先: {output}")
            print(f"処理時間: {elapsed:.1f}秒")

        except Exception as e:
            self.update_status(f"エラー: {e}")
            print("エラー:", e)

        finally:
            if writer is not None:
                writer.release()

            self.start_button.config(state="normal")


root = tk.Tk()
app = StripeGridApp(root)
root.mainloop()
