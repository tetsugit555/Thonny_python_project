
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
        root.title("RGB Stripe & Grid - Collision Edition")
        root.geometry("560x660")

        self.path = tk.StringVar()
        self.horizontal_time = tk.StringVar(value="20")
        self.vertical_time = tk.StringVar(value="20")
        self.grid_time = tk.StringVar(value="30")
        self.pause_time = tk.StringVar(value="2")
        self.final_time = tk.StringVar(value="5")
        self.intro_time = tk.StringVar(value="3")
        self.data_format = tk.StringVar(value="hex")
        self.max_events = tk.StringVar(value="8")
        self.status = tk.StringVar(value="BMPを選択してください")

        frame = ttk.Frame(root, padding=15)
        frame.pack(fill="both", expand=True)

        ttk.Button(
            frame, text="BMP画像を選択",
            command=self.choose_image
        ).pack(fill="x", pady=4)

        ttk.Label(
            frame, textvariable=self.path,
            wraplength=510
        ).pack()

        settings = [
            ("元画像の表示時間（秒）", self.intro_time),
            ("横ストライプ変換時間（秒）", self.horizontal_time),
            ("縦ストライプ変換時間（秒）", self.vertical_time),
            ("グリッド変換時間（秒）", self.grid_time),
            ("各ストライプ完成後の静止時間（秒）", self.pause_time),
            ("グリッド完成後の静止時間（秒）", self.final_time),
            ("同時衝突エフェクト最大数", self.max_events)
        ]

        for label, variable in settings:
            ttk.Label(frame, text=label).pack(pady=(6, 0))
            ttk.Entry(
                frame, textvariable=variable
            ).pack(fill="x")

        ttk.Label(
            frame, text="RGBデータ表示形式"
        ).pack(pady=(10, 3))

        ttk.Radiobutton(
            frame, text="通常 (R, G, B)",
            variable=self.data_format, value="rgb"
        ).pack(anchor="w")

        ttk.Radiobutton(
            frame, text="16進数 #RRGGBB",
            variable=self.data_format, value="hex"
        ).pack(anchor="w")

        self.start_button = ttk.Button(
            frame, text="MP4動画を作成",
            command=self.create_video
        )
        self.start_button.pack(fill="x", pady=12)

        ttk.Label(
            frame, textvariable=self.status,
            wraplength=510
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

    def make_motion(self, count, duration, rng):
        starts = rng.uniform(
            0, duration * 0.55, size=count
        )
        travel = (duration - starts) * rng.uniform(
            0.45, 1.0, size=count
        )
        return starts, travel

    def get_positions(self, t, starts, travel, length):
        progress = np.clip(
            (t - starts) / travel, 0, 1
        )
        return np.floor(
            progress * length
        ).astype(np.int32)

    def rgb_text(self, color):
        r, g, b = [int(v) for v in color]
        if self.data_format.get() == "hex":
            return f"#{r:02X}{g:02X}{b:02X}"
        return f"({r},{g},{b})"

    def draw_text(self, frame, text, x, y,
                  color, alpha=1.0, scale=0.55):
        if alpha <= 0:
            return

        overlay = frame.copy()
        cv2.putText(
            overlay, text, (int(x), int(y)),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale, color, 1, cv2.LINE_AA
        )
        cv2.addWeighted(
            overlay, alpha, frame,
            1 - alpha, 0, frame
        )

    def draw_collision(self, frame, event, now):
        age = now - event["start"]
        x, y = event["x"], event["y"]

        if age < 0 or age > 3.2:
            return

        a_text = event["a_text"]
        b_text = event["b_text"]
        d_text = event["d_text"]

        # 0-0.6秒: 左右から接近
        if age < 0.6:
            p = age / 0.6
            offset = 140 * (1 - p) + 15

            self.draw_text(
                frame, a_text,
                x - offset - 90, y,
                (255, 190, 110),
                scale=0.48
            )
            self.draw_text(
                frame, b_text,
                x + offset, y,
                (110, 190, 255),
                scale=0.48
            )

        # 0.6-1.0秒: 衝突・破片
        elif age < 1.0:
            p = (age - 0.6) / 0.4

            rng = np.random.default_rng(
                event["seed"]
            )

            for i in range(24):
                angle = rng.uniform(0, 2 * math.pi)
                speed = rng.uniform(15, 110)
                px = int(
                    x + math.cos(angle) * speed * p
                )
                py = int(
                    y + math.sin(angle) * speed * p
                )

                size = int(rng.integers(2, 7))
                color = (
                    (255, 180, 90)
                    if i % 2 else (130, 170, 255)
                )

                cv2.rectangle(
                    frame,
                    (px, py),
                    (px + size, py + size),
                    color, -1
                )

            self.draw_text(
                frame, "### ERROR ###",
                x - 80, y,
                (220, 220, 255),
                alpha=1-p,
                scale=0.5
            )

        # 1.0-3.2秒: 結果が出現して消える
        else:
            p = age - 1.0

            if p < 0.35:
                alpha = p / 0.35
            elif p < 1.8:
                alpha = 1.0
            else:
                alpha = max(
                    0, (2.2 - p) / 0.4
                )

            drift = int(p * 9)

            self.draw_text(
                frame, d_text,
                x - 55, y - drift,
                (230, 170, 255),
                alpha=alpha,
                scale=0.65
            )

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
            intro = float(self.intro_time.get())
            max_events = int(self.max_events.get())

            if min(h_time, v_time, g_time) <= 0:
                raise ValueError
            if min(pause, final, intro) < 0:
                raise ValueError
            if max_events < 1:
                raise ValueError

        except ValueError:
            self.update_status("設定値を確認してください")
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

            row_colors = np.rint(
                rgb.mean(axis=1)
            ).astype(np.uint8)

            col_colors = np.rint(
                rgb.mean(axis=0)
            ).astype(np.uint8)

            horizontal_rgb = np.broadcast_to(
                row_colors[:, None, :], rgb.shape
            ).copy()

            vertical_rgb = np.broadcast_to(
                col_colors[None, :, :], rgb.shape
            ).copy()

            grid_rgb = np.abs(
                horizontal_rgb.astype(np.int16)
                - vertical_rgb.astype(np.int16)
            ).astype(np.uint8)

            original = cv2.cvtColor(
                rgb, cv2.COLOR_RGB2BGR
            )
            horizontal = cv2.cvtColor(
                horizontal_rgb, cv2.COLOR_RGB2BGR
            )
            vertical = cv2.cvtColor(
                vertical_rgb, cv2.COLOR_RGB2BGR
            )
            grid = cv2.cvtColor(
                grid_rgb, cv2.COLOR_RGB2BGR
            )

            fps = 30
            out_w = width + width % 2
            out_h = height + height % 2

            def fit_frame(frame):
                if out_w == width and out_h == height:
                    return frame
                return cv2.copyMakeBorder(
                    frame, 0, out_h-height,
                    0, out_w-width,
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
                raise RuntimeError("MP4を作成できません")

            rng = np.random.default_rng()

            def write(frame):
                writer.write(fit_frame(frame))

            def hold(frame, seconds):
                for _ in range(round(seconds * fps)):
                    write(frame)

            def scan(base, target, duration, axis, title):
                canvas = base.copy()
                count = height if axis == "row" else width
                length = width if axis == "row" else height

                starts, travel = self.make_motion(
                    count, duration, rng
                )
                previous = np.zeros(count, dtype=np.int32)
                frames = max(1, math.ceil(duration * fps))

                for f in range(frames):
                    t = duration * (f + 1) / frames
                    positions = self.get_positions(
                        t, starts, travel, length
                    )

                    for index in np.flatnonzero(
                        positions > previous
                    ):
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

            # 1. 元画像
            hold(original, intro)

            # 2. 横ストライプ
            canvas = scan(
                original, horizontal,
                h_time, "row", "横ストライプ"
            )
            hold(canvas, pause)

            # 3. 縦ストライプ
            canvas = scan(
                canvas, vertical,
                v_time, "col", "縦ストライプ"
            )
            hold(canvas, pause)

            # 4. グリッド＋RGB衝突
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

            row_passed = np.zeros(
                (height, width), dtype=bool
            )
            col_passed = np.zeros(
                (height, width), dtype=bool
            )

            events = []
            frames = max(1, math.ceil(g_time * fps))

            for f in range(frames):
                t = g_time * (f + 1) / frames

                row_x = self.get_positions(
                    t, row_starts, row_travel, width
                )
                col_y = self.get_positions(
                    t, col_starts, col_travel, height
                )

                for y in np.flatnonzero(
                    row_x > row_previous
                ):
                    row_passed[
                        y, row_previous[y]:row_x[y]
                    ] = True

                for x in np.flatnonzero(
                    col_y > col_previous
                ):
                    col_passed[
                        col_previous[x]:col_y[x], x
                    ] = True

                intersection = row_passed & col_passed
                canvas[intersection] = grid[intersection]

                row_previous = row_x
                col_previous = col_y

                # 終了したイベントを除去
                events = [
                    e for e in events
                    if t - e["start"] < 3.2
                ]

                # 実際の交差領域からランダムに選ぶ
                if len(events) < max_events:
                    if rng.random() < 0.35:
                        ys, xs = np.where(intersection)

                        if len(xs) > 0:
                            k = rng.integers(0, len(xs))
                            x = int(xs[k])
                            y = int(ys[k])

                            a_color = row_colors[y]
                            b_color = col_colors[x]
                            d_color = grid_rgb[y, x]

                            events.append({
                                "x": x,
                                "y": y,
                                "start": t,
                                "seed": int(
                                    rng.integers(0, 1000000)
                                ),
                                "a_text": self.rgb_text(
                                    a_color
                                ),
                                "b_text": self.rgb_text(
                                    b_color
                                ),
                                "d_text": self.rgb_text(
                                    d_color
                                )
                            })

                # 元のグリッド画像を汚さず、
                # 表示用フレームだけにエフェクトを描く
                display = canvas.copy()

                for event in events:
                    self.draw_collision(
                        display, event, t
                    )

                write(display)

                if f % 30 == 0:
                    self.update_status(
                        f"グリッド＋衝突: {f+1}/{frames}"
                    )

            # 最後はエフェクトなしの完成画像
            hold(grid, final)

            elapsed = time.time() - start_clock
            self.update_status("動画作成完了！")

            print("動画作成完了！")
            print(f"画像サイズ: {width} x {height}")
            print(f"保存先: {output}")
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
