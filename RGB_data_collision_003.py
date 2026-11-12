
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image
import numpy as np
import cv2
import math
import time


class StripeGridApp:

    FPS = 30
    FONT = cv2.FONT_HERSHEY_SIMPLEX

    def __init__(self, root):
        self.root = root
        root.title("RGB Stripe & Grid - Floating Data 2")
        root.geometry("590x760")

        self.path = tk.StringVar()
        self.intro_time = tk.StringVar(value="3")
        self.horizontal_time = tk.StringVar(value="20")
        self.vertical_time = tk.StringVar(value="20")
        self.grid_time = tk.StringVar(value="40")
        self.pause_time = tk.StringVar(value="2")
        self.final_time = tk.StringVar(value="5")

        self.data_format = tk.StringVar(value="hex")
        self.max_events = tk.StringVar(value="6")
        self.stream_count = tk.StringVar(value="18")
        self.brightness = tk.DoubleVar(value=55)
        self.status = tk.StringVar(value="BMPを選択してください")

        frame = ttk.Frame(root, padding=15)
        frame.pack(fill="both", expand=True)

        ttk.Button(
            frame, text="BMP画像を選択",
            command=self.choose_image
        ).pack(fill="x", pady=4)

        ttk.Label(
            frame, textvariable=self.path,
            wraplength=530
        ).pack()

        settings = [
            ("元画像の表示時間（秒）", self.intro_time),
            ("横ストライプ変換時間（秒）", self.horizontal_time),
            ("縦ストライプ変換時間（秒）", self.vertical_time),
            ("グリッド変換時間（秒）", self.grid_time),
            ("ストライプ完成後の静止時間（秒）", self.pause_time),
            ("グリッド完成後の静止時間（秒）", self.final_time),
            ("同時RGB融合イベント最大数", self.max_events),
            ("背景RGBデータ列の数", self.stream_count)
        ]

        for label, variable in settings:
            ttk.Label(frame, text=label).pack(pady=(5, 0))
            ttk.Entry(
                frame, textvariable=variable
            ).pack(fill="x")

        ttk.Label(
            frame, text="RGBデータ表示形式"
        ).pack(pady=(10, 3))

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

        ttk.Label(
            frame, text="背景RGB文字の明るさ"
        ).pack(pady=(10, 2))

        self.brightness_label = ttk.Label(
            frame, text="55%"
        )
        self.brightness_label.pack()

        ttk.Scale(
            frame,
            from_=0, to=100,
            variable=self.brightness,
            command=self.on_brightness_change
        ).pack(fill="x")

        self.start_button = ttk.Button(
            frame, text="MP4動画を作成",
            command=self.create_video
        )
        self.start_button.pack(fill="x", pady=12)

        ttk.Label(
            frame, textvariable=self.status,
            wraplength=530
        ).pack()

        self.base_scale = 0.5

    def on_brightness_change(self, value):
        self.brightness_label.config(
            text=f"{float(value):.0f}%"
        )

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

    def rgb_text(self, color):
        r, g, b = [int(v) for v in color]
        if self.data_format.get() == "hex":
            return f"#{r:02X}{g:02X}{b:02X}"
        return f"({r},{g},{b})"

    def calculate_font_scale(self, image_height):
        # 文字の高さを画像の縦サイズの1/100に
        (_, reference_height), _ = cv2.getTextSize(
            "RGB0123456789",
            self.FONT, 1.0, 1
        )
        return (image_height / 100.0) / max(
            1, reference_height
        )

    def text_width(self, text, scale):
        (w, _), _ = cv2.getTextSize(
            text, self.FONT, scale, 1
        )
        return w

    def draw_text(
        self, frame, text, x, y,
        alpha=1.0, scale=None,
        brightness=230
    ):
        if alpha <= 0:
            return

        if scale is None:
            scale = self.base_scale

        height, width = frame.shape[:2]

        (tw, th), baseline = cv2.getTextSize(
            text, self.FONT, scale, 1
        )

        x = int(round(x))
        y = int(round(y))

        if x >= width or x + tw < 0:
            return
        if y - th >= height or y + baseline < 0:
            return

        # 文字が存在する範囲だけ合成
        # フレーム全体を毎回コピーしない
        x0 = max(0, x - 2)
        x1 = min(width, x + tw + 3)
        y0 = max(0, y - th - 3)
        y1 = min(height, y + baseline + 3)

        if x1 <= x0 or y1 <= y0:
            return

        roi = frame[y0:y1, x0:x1]
        overlay = roi.copy()

        value = int(np.clip(brightness, 0, 255))

        cv2.putText(
            overlay, text,
            (x - x0, y - y0),
            self.FONT, scale,
            (value, value, value),
            1, cv2.LINE_AA
        )

        cv2.addWeighted(
            overlay,
            float(np.clip(alpha, 0, 1)),
            roi,
            1 - float(np.clip(alpha, 0, 1)),
            0,
            roi
        )

    @staticmethod
    def smoothstep(p):
        p = max(0.0, min(1.0, p))
        return p * p * (3 - 2 * p)

    def make_motion(self, count, duration, rng):
        starts = rng.uniform(
            0, duration * 0.55, size=count
        )
        travel = (duration - starts) * rng.uniform(
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

    # ==========================================
    # 背景を流れるRGBデータ
    # ==========================================

    def make_stream(
        self, width, height, rng, palette,
        direction=None, entering=False
    ):
        depth = float(rng.uniform(0.25, 1.0))

        # 文字の大きさは縦サイズを基準に
        scale = self.base_scale * (
            0.65 + 0.75 * depth
        )

        # 速度は横幅を基準に決定
        # 生成後は変化させない
        speed = width * float(
            rng.uniform(0.012, 0.065)
        ) * (0.45 + 0.55 * depth)

        # 列ごとの明るさの違い
        brightness = int(
            255 * (0.35 + 0.65 * depth)
        )

        alpha = float(
            rng.uniform(0.25, 0.75)
        )

        text_count = int(rng.integers(5, 14))

        texts = [
            self.rgb_text(
                palette[int(rng.integers(len(palette)))]
            )
            for _ in range(text_count)
        ]

        gap = height * float(
            rng.uniform(0.012, 0.05)
        )

        advance = max(
            self.text_width(s, scale)
            for s in texts
        ) + gap

        total = advance * text_count

        if direction is None:
            direction = int(rng.choice([-1, 1]))

        if entering:
            x = -total if direction == 1 else width
        else:
            x = float(rng.uniform(-total, width))

        y = float(
            rng.uniform(
                max(10, height * 0.04),
                max(11, height * 0.96)
            )
        )

        return {
            "x": x,
            "y": y,
            "speed": speed,
            "direction": direction,
            "scale": scale,
            "brightness": brightness,
            "alpha": alpha,
            "texts": texts,
            "advance": advance,
            "total": total
        }

    def draw_streams(
        self, frame, streams, dt,
        width, height, rng, palette,
        brightness_multiplier
    ):
        for i, stream in enumerate(streams):

            # 等速運動：途中で速度は変えない
            stream["x"] += (
                stream["speed"]
                * stream["direction"]
                * dt
            )

            x = stream["x"]
            total = stream["total"]

            exited = (
                stream["direction"] == 1
                and x > width
            ) or (
                stream["direction"] == -1
                and x + total < 0
            )

            if exited:
                stream = self.make_stream(
                    width, height, rng, palette,
                    direction=stream["direction"],
                    entering=True
                )
                streams[i] = stream

            effective_brightness = int(
                stream["brightness"]
                * brightness_multiplier
            )

            if effective_brightness <= 0:
                continue

            for j, text in enumerate(stream["texts"]):
                tx = (
                    stream["x"]
                    + j * stream["advance"]
                )

                self.draw_text(
                    frame, text,
                    tx, stream["y"],
                    alpha=stream["alpha"],
                    scale=stream["scale"],
                    brightness=effective_brightness
                )

    # ==========================================
    # RGBデータの融合演出
    # ==========================================

    def make_collision(
        self, x, y, now,
        a_color, b_color, d_color,
        width, height, rng
    ):
        a_text = self.rgb_text(a_color)
        b_text = self.rgb_text(b_color)
        d_text = self.rgb_text(d_color)

        scale = self.base_scale * float(
            rng.uniform(1.0, 1.4)
        )

        # イベントごとに接近時間をランダム化
        approach = float(rng.uniform(2.0, 4.0))
        fade_in = float(rng.uniform(0.6, 1.0))
        hold = 1.5
        fade_out = 0.7

        wa = self.text_width(a_text, scale)
        wb = self.text_width(b_text, scale)
        wd = self.text_width(d_text, scale)

        margin = max(wa, wb, wd) / 2 + 3

        if width > margin * 2:
            cx = float(np.clip(
                x, margin, width - margin
            ))
        else:
            cx = width / 2

        cy = float(np.clip(
            y,
            max(12, height * 0.05),
            max(12, height * 0.95)
        ))

        return {
            "x": cx,
            "y": cy,
            "start": now,
            "approach": approach,
            "fade_in": fade_in,
            "hold": hold,
            "fade_out": fade_out,
            "total": (
                approach + fade_in + hold + fade_out
            ),
            "a_text": a_text,
            "b_text": b_text,
            "d_text": d_text,
            "scale": scale
        }

    def draw_collision(
        self, frame, event, now, width
    ):
        age = now - event["start"]

        if age < 0 or age >= event["total"]:
            return

        cx = event["x"]
        cy = event["y"]
        scale = event["scale"]

        a_text = event["a_text"]
        b_text = event["b_text"]
        d_text = event["d_text"]

        wa = self.text_width(a_text, scale)
        wb = self.text_width(b_text, scale)
        wd = self.text_width(d_text, scale)

        approach = event["approach"]

        if age < approach:
            p = self.smoothstep(age / approach)

            # 左側の文字は左端の外から
            lx = (
                -wa - 5
                + (cx - wa / 2 + wa + 5) * p
            )

            # 右側の文字は右端の外から
            rx = (
                width + 5
                + (cx - wb / 2 - width - 5) * p
            )

            # 接近終盤で静かに消える
            if p < 0.60:
                alpha = 0.78
            else:
                alpha = 0.78 * (
                    1 - self.smoothstep(
                        (p - 0.60) / 0.40
                    )
                )

            self.draw_text(
                frame, a_text,
                lx, cy,
                alpha=alpha,
                scale=scale,
                brightness=230
            )

            self.draw_text(
                frame, b_text,
                rx, cy,
                alpha=alpha,
                scale=scale,
                brightness=230
            )

        else:
            p = age - approach

            fade_in = event["fade_in"]
            hold = event["hold"]
            fade_out = event["fade_out"]

            if p < fade_in:
                alpha = (
                    self.smoothstep(p / fade_in)
                    * 0.88
                )
            elif p < fade_in + hold:
                alpha = 0.88
            else:
                q = (
                    p - fade_in - hold
                ) / fade_out

                alpha = (
                    1 - self.smoothstep(q)
                ) * 0.88

            drift = min(
                1.0,
                p / (fade_in + hold + fade_out)
            ) * self.image_height * 0.012

            self.draw_text(
                frame, d_text,
                cx - wd / 2,
                cy - drift,
                alpha=alpha,
                scale=scale,
                brightness=240
            )

    # ==========================================
    # MP4作成
    # ==========================================

    def create_video(self):
        if not self.path.get():
            self.update_status("BMPを選択してください")
            return

        try:
            intro = float(self.intro_time.get())
            h_time = float(self.horizontal_time.get())
            v_time = float(self.vertical_time.get())
            g_time = float(self.grid_time.get())
            pause = float(self.pause_time.get())
            final = float(self.final_time.get())

            max_events = int(self.max_events.get())
            stream_count = int(self.stream_count.get())

            brightness_multiplier = (
                self.brightness.get() / 100.0
            )

            if min(h_time, v_time, g_time) <= 0:
                raise ValueError

            if min(intro, pause, final) < 0:
                raise ValueError

            if max_events < 1 or stream_count < 0:
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
            clock = time.time()
            self.update_status("BMP解析中...")

            with Image.open(self.path.get()) as img:
                rgb = np.array(img.convert("RGB"))

            height, width = rgb.shape[:2]
            self.image_height = height

            # 画像高さに比例する文字サイズ
            self.base_scale = self.calculate_font_scale(
                height
            )

            row_colors = np.rint(
                rgb.mean(axis=1)
            ).astype(np.uint8)

            col_colors = np.rint(
                rgb.mean(axis=0)
            ).astype(np.uint8)

            horizontal_rgb = np.broadcast_to(
                row_colors[:, None, :],
                rgb.shape
            ).copy()

            vertical_rgb = np.broadcast_to(
                col_colors[None, :, :],
                rgb.shape
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

            fps = self.FPS
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

            def hold_frame(frame, seconds):
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

                frames = max(
                    1, math.ceil(duration * fps)
                )

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
            hold_frame(original, intro)

            # 2. 横ストライプ
            canvas = scan(
                original, horizontal,
                h_time, "row", "横ストライプ"
            )
            hold_frame(canvas, pause)

            # 3. 縦ストライプ
            canvas = scan(
                canvas, vertical,
                v_time, "col", "縦ストライプ"
            )
            hold_frame(canvas, pause)

            # 4. グリッド＋RGBデータ融合
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

            # RGBストリームに使う色も元BMPから取得
            flat_rgb = rgb.reshape(-1, 3)
            palette_size = min(
                10000, len(flat_rgb)
            )

            sample_indices = rng.choice(
                len(flat_rgb),
                size=palette_size,
                replace=False
            )
            palette = flat_rgb[sample_indices]

            streams = [
                self.make_stream(
                    width, height, rng, palette
                )
                for _ in range(stream_count)
            ]

            events = []
            candidate_points = []
            previous_intersection = np.zeros(
                (height, width), dtype=bool
            )

            frames = max(
                1, math.ceil(g_time * fps)
            )

            for f in range(frames):
                t = g_time * (f + 1) / frames
                dt = g_time / frames

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

                intersection = (
                    row_passed & col_passed
                )

                # 今回新しく交差した座標
                newly = (
                    intersection & ~previous_intersection
                )

                ys, xs = np.where(newly)

                # グリッド更新
                canvas[intersection] = grid[intersection]

                previous_intersection = intersection.copy()
                row_previous = row_x
                col_previous = col_y

                if len(xs) > 0:
                    sample_n = min(12, len(xs))
                    picks = rng.choice(
                        len(xs),
                        size=sample_n,
                        replace=False
                    )

                    for k in picks:
                        candidate_points.append(
                            (int(xs[k]), int(ys[k]))
                        )

                if len(candidate_points) > 500:
                    candidate_points = candidate_points[-500:]

                # 完了した融合イベントを除去
                events = [
                    e for e in events
                    if t - e["start"] < e["total"]
                ]

                # ランダムに融合イベント発生
                if (
                    len(events) < max_events
                    and candidate_points
                    and rng.random() < 0.16
                ):
                    index = int(
                        rng.integers(len(candidate_points))
                    )
                    x, y = candidate_points.pop(index)

                    events.append(
                        self.make_collision(
                            x, y, t,
                            row_colors[y],
                            col_colors[x],
                            grid_rgb[y, x],
                            width, height, rng
                        )
                    )

                display = canvas.copy()

                # 背景のRGBデータ列
                self.draw_streams(
                    display, streams, dt,
                    width, height, rng, palette,
                    brightness_multiplier
                )

                # 左右から融合するRGBデータ
                for event in events:
                    self.draw_collision(
                        display, event, t, width
                    )

                write(display)

                if f % 30 == 0:
                    self.update_status(
                        f"グリッド生成: {f+1}/{frames}"
                    )

            # 5. 完成画像
            hold_frame(grid, final)

            elapsed = time.time() - clock
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
