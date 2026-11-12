
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
        root.title("RGB Stripe & Grid - Floating Data")
        root.geometry("570x720")

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
        self.status = tk.StringVar(value="BMPを選択してください")

        frame = ttk.Frame(root, padding=15)
        frame.pack(fill="both", expand=True)

        ttk.Button(
            frame,
            text="BMP画像を選択",
            command=self.choose_image
        ).pack(fill="x", pady=4)

        ttk.Label(
            frame,
            textvariable=self.path,
            wraplength=520
        ).pack()

        settings = [
            ("元画像の表示時間（秒）", self.intro_time),
            ("横ストライプ変換時間（秒）", self.horizontal_time),
            ("縦ストライプ変換時間（秒）", self.vertical_time),
            ("グリッド変換時間（秒）", self.grid_time),
            ("各ストライプ完成後の静止時間（秒）", self.pause_time),
            ("グリッド完成後の静止時間（秒）", self.final_time),
            ("同時に進行するRGB融合イベント数", self.max_events),
            ("背景を流れるRGBデータ列の数", self.stream_count)
        ]

        for label, variable in settings:
            ttk.Label(
                frame, text=label
            ).pack(pady=(5, 0))

            ttk.Entry(
                frame, textvariable=variable
            ).pack(fill="x")

        ttk.Label(
            frame,
            text="RGBデータ表示形式"
        ).pack(pady=(10, 3))

        ttk.Radiobutton(
            frame,
            text="通常 (R, G, B)",
            variable=self.data_format,
            value="rgb"
        ).pack(anchor="w")

        ttk.Radiobutton(
            frame,
            text="16進数 #RRGGBB",
            variable=self.data_format,
            value="hex"
        ).pack(anchor="w")

        self.start_button = ttk.Button(
            frame,
            text="MP4動画を作成",
            command=self.create_video
        )
        self.start_button.pack(fill="x", pady=12)

        ttk.Label(
            frame,
            textvariable=self.status,
            wraplength=520
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

    def rgb_text(self, color):
        r, g, b = [int(v) for v in color]

        if self.data_format.get() == "hex":
            return f"#{r:02X}{g:02X}{b:02X}"

        return f"({r},{g},{b})"

    def text_width(self, text, scale):
        (w, h), baseline = cv2.getTextSize(
            text,
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            1
        )
        return w

    def draw_text(
        self, frame, text, x, y,
        alpha=1.0, scale=0.55,
        brightness=220
    ):
        if alpha <= 0:
            return

        h, w = frame.shape[:2]
        tw = self.text_width(text, scale)

        # 完全に画面外なら描画しない
        if x > w or x + tw < 0:
            return
        if y < -20 or y > h + 20:
            return

        # 白系の文字
        value = int(np.clip(brightness, 0, 255))
        color = (value, value, value)

        overlay = frame.copy()

        cv2.putText(
            overlay,
            text,
            (int(x), int(y)),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            1,
            cv2.LINE_AA
        )

        cv2.addWeighted(
            overlay,
            float(np.clip(alpha, 0, 1)),
            frame,
            1 - float(np.clip(alpha, 0, 1)),
            0,
            frame
        )

    @staticmethod
    def smoothstep(p):
        p = max(0.0, min(1.0, p))
        return p * p * (3 - 2 * p)

    def make_motion(self, count, duration, rng):
        starts = rng.uniform(
            0, duration * 0.55,
            size=count
        )

        travel = (duration - starts) * rng.uniform(
            0.45, 1.0,
            size=count
        )

        return starts, travel

    def get_positions(
        self, t, starts, travel, length
    ):
        progress = np.clip(
            (t - starts) / travel,
            0, 1
        )

        return np.floor(
            progress * length
        ).astype(np.int32)

    # -----------------------------------------
    # 背景のRGBデータストリーム
    # -----------------------------------------

    def make_stream(self, width, height, rng, palette):
        scale = float(rng.uniform(0.30, 0.70))
        speed = float(rng.uniform(12, 85))
        brightness = int(rng.integers(105, 240))
        alpha = float(rng.uniform(0.18, 0.65))

        # 奥にある文字ほど小さく、暗く、遅く
        depth = float(rng.uniform(0.25, 1.0))

        scale *= 0.6 + 0.4 * depth
        speed *= 0.4 + 0.6 * depth
        brightness = int(
            brightness * (0.45 + 0.55 * depth)
        )
        alpha *= 0.5 + 0.5 * depth

        text_count = int(rng.integers(5, 15))

        texts = []
        for _ in range(text_count):
            index = int(rng.integers(0, len(palette)))
            texts.append(
                self.rgb_text(palette[index])
            )

        gap = float(rng.uniform(20, 90))

        # 横に並んだデータの列
        advance = max(
            self.text_width(s, scale)
            for s in texts
        ) + gap

        total_length = advance * text_count

        # 画面のランダムな位置から流れ始める
        x = float(
            rng.uniform(-total_length, width)
        )

        y = float(
            rng.uniform(25, max(26, height - 10))
        )

        direction = int(
            rng.choice([-1, 1])
        )

        return {
            "x": x,
            "y": y,
            "speed": speed,
            "scale": scale,
            "brightness": brightness,
            "alpha": alpha,
            "texts": texts,
            "advance": advance,
            "total": total_length,
            "direction": direction
        }

    def draw_streams(
        self, frame, streams, dt,
        width, height, rng, palette
    ):
        for i, stream in enumerate(streams):

            stream["x"] += (
                stream["speed"]
                * stream["direction"]
                * dt
            )

            x = stream["x"]
            total = stream["total"]

            # 完全に画面外へ出たら新しい列を生成
            if (
                stream["direction"] == 1
                and x > width + 20
            ) or (
                stream["direction"] == -1
                and x + total < -20
            ):
                new_stream = self.make_stream(
                    width, height, rng, palette
                )

                if stream["direction"] == 1:
                    new_stream["x"] = -new_stream["total"]
                else:
                    new_stream["x"] = width + 10

                streams[i] = new_stream
                stream = new_stream

            for j, text in enumerate(stream["texts"]):
                tx = (
                    stream["x"]
                    + j * stream["advance"]
                )

                self.draw_text(
                    frame,
                    text,
                    tx,
                    stream["y"],
                    alpha=stream["alpha"],
                    scale=stream["scale"],
                    brightness=stream["brightness"]
                )

    # -----------------------------------------
    # RGBデータの静かな融合
    # -----------------------------------------

    def make_collision(
        self, x, y, now,
        a_color, b_color, d_color,
        width, height, rng
    ):
        a_text = self.rgb_text(a_color)
        b_text = self.rgb_text(b_color)
        d_text = self.rgb_text(d_color)

        scale = float(rng.uniform(0.42, 0.65))

        # 移動時間はイベントごとにランダム
        approach = float(rng.uniform(2.0, 4.0))

        fade = float(rng.uniform(0.65, 1.0))

        # 交差地点の近くで融合する
        # 文字が画面内に収まりやすいよう調整
        margin = max(
            self.text_width(a_text, scale),
            self.text_width(b_text, scale),
            self.text_width(d_text, scale)
        ) // 2 + 5

        cx = int(np.clip(
            x, min(margin, width // 2),
            max(width - margin, width // 2)
        ))

        cy = int(np.clip(
            y, 25, max(25, height - 15)
        ))

        return {
            "x": cx,
            "y": cy,
            "start": now,
            "approach": approach,
            "fade": fade,
            "a_text": a_text,
            "b_text": b_text,
            "d_text": d_text,
            "scale": scale,
            "total": approach + fade + 2.3
        }

    def draw_collision(
        self, frame, event, now,
        width
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
        fade = event["fade"]

        # 左右の文字は必ず画面の外から出発
        left_start = -wa - 8
        right_start = width + 8

        # 衝突地点の左右に接近
        left_end = cx - wa / 2
        right_end = cx - wb / 2

        if age < approach:

            p = self.smoothstep(age / approach)

            lx = (
                left_start
                + (left_end - left_start) * p
            )

            rx = (
                right_start
                + (right_end - right_start) * p
            )

            # 接近の終盤にふわっと消える
            fade_start = 0.65

            if p > fade_start:
                alpha = 1.0 - self.smoothstep(
                    (p - fade_start)
                    / (1.0 - fade_start)
                )
            else:
                alpha = 0.78

            self.draw_text(
                frame, a_text,
                lx, cy,
                alpha=alpha,
                scale=scale,
                brightness=225
            )

            self.draw_text(
                frame, b_text,
                rx, cy,
                alpha=alpha,
                scale=scale,
                brightness=225
            )

        else:
            p = age - approach

            # 絶対差分がゆっくり出現
            if p < fade:
                alpha = self.smoothstep(p / fade) * 0.88

            # 約2秒間表示
            elif p < fade + 1.7:
                alpha = 0.88

            # ゆっくり消える
            else:
                q = (
                    p - fade - 1.7
                ) / 0.6

                alpha = (
                    1 - self.smoothstep(q)
                ) * 0.88

            # 少しだけ上へ漂う
            drift = 8 * min(
                1.0, p / 2.3
            )

            self.draw_text(
                frame,
                d_text,
                cx - wd / 2,
                cy - drift,
                alpha=alpha,
                scale=scale * 1.05,
                brightness=240
            )

    # -----------------------------------------
    # MP4作成
    # -----------------------------------------

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
                rgb = np.array(
                    img.convert("RGB")
                )

            height, width = rgb.shape[:2]

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

            fps = 30
            out_w = width + width % 2
            out_h = height + height % 2

            def fit_frame(frame):
                if (
                    out_w == width
                    and out_h == height
                ):
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

                count = (
                    height if axis == "row"
                    else width
                )

                length = (
                    width if axis == "row"
                    else height
                )

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

            # =====================================
            # 1. 元画像
            # =====================================

            hold(original, intro)

            # =====================================
            # 2. 横ストライプ
            # =====================================

            canvas = scan(
                original,
                horizontal,
                h_time,
                "row",
                "横ストライプ"
            )

            hold(canvas, pause)

            # =====================================
            # 3. 縦ストライプ
            # =====================================

            canvas = scan(
                canvas,
                vertical,
                v_time,
                "col",
                "縦ストライプ"
            )

            hold(canvas, pause)

            # =====================================
            # 4. グリッド生成＋データ演出
            # =====================================

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

            # BMPから実際の色データを抽出
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
            frames = max(
                1, math.ceil(g_time * fps)
            )

            # イベントを発生させるための
            # 交差地点の候補
            candidate_points = []

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

                # 新しく交差したピクセルだけ取得
                newly = (
                    intersection
                    & (canvas != grid).any(axis=2)
                )

                ys, xs = np.where(newly)

                # 実際のグリッドを更新
                canvas[intersection] = grid[intersection]

                row_previous = row_x
                col_previous = col_y

                # 新しい交差点を候補に追加
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

                # 候補が増えすぎないようにする
                if len(candidate_points) > 500:
                    candidate_points = (
                        candidate_points[-500:]
                    )

                # 終了イベントを除去
                events = [
                    e for e in events
                    if t - e["start"] < e["total"]
                ]

                # 衝突イベントをランダムに発生
                if (
                    len(events) < max_events
                    and candidate_points
                    and rng.random() < 0.16
                ):
                    index = int(
                        rng.integers(
                            0, len(candidate_points)
                        )
                    )

                    x, y = candidate_points.pop(index)

                    event = self.make_collision(
                        x, y, t,
                        row_colors[y],
                        col_colors[x],
                        grid_rgb[y, x],
                        width, height, rng
                    )

                    events.append(event)

                # 描画用フレーム
                display = canvas.copy()

                # 背景RGBデータの流れ
                self.draw_streams(
                    display,
                    streams,
                    dt,
                    width,
                    height,
                    rng,
                    palette
                )

                # 左右から接近するRGBデータ
                for event in events:
                    self.draw_collision(
                        display,
                        event,
                        t,
                        width
                    )

                write(display)

                if f % 30 == 0:
                    self.update_status(
                        f"グリッド生成: {f+1}/{frames}"
                    )

            # =====================================
            # 5. 完成グリッド
            # =====================================

            hold(grid, final)

            elapsed = time.time() - clock

            self.update_status("動画作成完了！")

            print("動画作成完了！")
            print(f"画像サイズ: {width} x {height}")
            print(f"保存先: {output}")
            print(f"処理時間: {elapsed:.1f}秒")

        except Exception as e:
            self.update_status(
                f"エラー: {e}"
            )
            print("エラー:", e)

        finally:
            if writer is not None:
                writer.release()

            self.start_button.config(
                state="normal"
            )


root = tk.Tk()
app = StripeGridApp(root)
root.mainloop()
