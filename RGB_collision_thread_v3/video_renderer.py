import math
import time
import numpy as np
import cv2
import os
import subprocess
import shutil
import tempfile
import threading
from tkinter import filedialog

from bmp_analyzer import analyze_bmp
from stripe_generator import create_stripes
from grid_generator import difference_grid

class VideoRendererMixin:
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
                self.brightness.get() / 100
            )
            speed_multiplier = (
                self.speed_percent.get() / 100
            )
            freeze_seconds = (
                self.freeze_seconds.get()
            )
            post_grid_motion_seconds = (
                self.post_grid_motion_seconds.get()
            )

            if not all(
                math.isfinite(v)
                for v in (
                    intro, h_time, v_time, g_time,
                    pause, final, freeze_seconds,
                    post_grid_motion_seconds
                )
            ):
                raise ValueError

            if min(h_time, v_time, g_time) <= 0:
                raise ValueError

            if min(intro, pause, final, freeze_seconds,
                   post_grid_motion_seconds) < 0:
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

        instagram_mode = self.output_mode.get() == "instagram"
        source_path = self.path.get()
        data_format = self.data_format.get()
        self.start_button.config(state="disabled")
        self.progress.start(12)
        self.update_status("動画生成を開始します...")

        # Tkinterの変数・ウィジェットはワーカースレッドで触らない。
        # すべての設定を通常のPython値として引き渡す。
        args = dict(
            source_path=source_path, output=output,
            instagram_mode=instagram_mode, data_format=data_format,
            intro=intro, h_time=h_time, v_time=v_time, g_time=g_time,
            pause=pause, final=final, max_events=max_events,
            stream_count=stream_count,
            brightness_multiplier=brightness_multiplier,
            speed_multiplier=speed_multiplier,
            freeze_seconds=freeze_seconds,
            post_grid_motion_seconds=post_grid_motion_seconds,
        )
        threading.Thread(
            target=self._render_video_worker, kwargs=args, daemon=True
        ).start()

    def _render_video_worker(
        self, source_path, output, instagram_mode, data_format,
        intro, h_time, v_time, g_time, pause, final, max_events,
        stream_count, brightness_multiplier, speed_multiplier,
        freeze_seconds, post_grid_motion_seconds,
    ):
        # rgb_text() の既存APIを保ちつつTk変数を参照しないようにする。
        # ワーカー専用のスナップショットを渡す。
        self._worker_data_format = data_format
        final_output = output
        temporary_output = None
        if instagram_mode:
            fd, temporary_output = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)
            output = temporary_output

        writer = None
        try:
            clock = time.time()
            self.update_status("BMP解析中...")

            data = analyze_bmp(source_path)
            rgb = data.rgb
            height, width = data.height, data.width
            self.image_height = height
            self.base_scale = self.calculate_font_scale(height)
            row_colors, col_colors = data.row_colors, data.col_colors
            horizontal_rgb, vertical_rgb = create_stripes(data)
            grid_rgb = difference_grid(horizontal_rgb, vertical_rgb)

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
                    0, out_h-height,
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
                base, target, duration, axis, title,
                lighten=False
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
                            if lighten:
                                # Photoshop「比較（明）」: B/G/R各成分の最大値
                                # 横ストライプを消さず、縦ストライプを重ねる
                                np.maximum(
                                    canvas[p0:p1, index],
                                    target[p0:p1, index],
                                    out=canvas[p0:p1, index]
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

                return canvas.copy()

            # ----------------------------------
            # 1. 元画像
            # ----------------------------------
            hold_frame(original, intro)

            # ----------------------------------
            # 2. 横ストライプ
            # ----------------------------------
            canvas = scan(
                original, horizontal,
                h_time, "row", "横ストライプ"
            )
            hold_frame(canvas, pause)

            # ----------------------------------
            # 3. 縦ストライプ
            # ----------------------------------
            canvas = scan(
                canvas, vertical,
                v_time, "col", "縦ストライプ",
                lighten=True
            )
            hold_frame(canvas, pause)

            # ----------------------------------
            # 4. グリッド生成
            # ----------------------------------
            # 比較（明）で重ねた横＋縦ストライプから開始
            # 交差部分は従来どおりRGB差分のグリッドに変換
            canvas = canvas.copy()

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

            previous_intersection = np.zeros(
                (height, width), dtype=bool
            )

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

            frames = max(
                1, math.ceil(g_time * fps)
            )

            # 最終フレームの文字状態を保存する
            last_glyphs = []

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

                newly = (
                    intersection & ~previous_intersection
                )

                ys, xs = np.where(newly)

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

                events = [
                    e for e in events
                    if t - e["start"] < e["total"]
                ]

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
                        self.make_collision_from_pixel(
                            horizontal_rgb, vertical_rgb,
                            x, y, t, rng
                        )
                    )

                # 背景データを移動
                self.advance_streams(
                    streams, dt,
                    width, height, rng, palette,
                    speed_multiplier
                )

                # このフレームの全文字を取得
                glyphs = self.stream_glyphs(
                    streams, brightness_multiplier
                )

                for event in events:
                    glyphs.extend(
                        self.collision_glyphs(
                            event, t, width
                        )
                    )

                display = canvas.copy()
                self.draw_glyphs(display, glyphs)
                write(display)

                # 最終フレームの文字を記録
                last_glyphs = glyphs

                if f % 30 == 0:
                    self.update_status(
                        f"グリッド生成: {f+1}/{frames}"
                    )

            # ----------------------------------
            # 5. 完成したグリッドを静止させ、RGB文字だけ動かす
            # ----------------------------------
            motion_frames = round(post_grid_motion_seconds * fps)
            for f in range(motion_frames):
                now = g_time + (f + 1) / fps
                self.advance_streams(
                    streams, 1.0 / fps,
                    width, height, rng, palette,
                    speed_multiplier
                )
                # 生成中に始まった融合演出も継続し、終了したものは除外
                events = [
                    e for e in events
                    if now - e["start"] < e["total"]
                ]

                # グリッド完成後も左右からRGBデータを衝突させる。
                # 座標ごとの横・縦ストライプ色から差の絶対値を再利用する。
                if len(events) < max_events and rng.random() < 0.16:
                    x = int(rng.integers(0, width))
                    y = int(rng.integers(0, height))
                    events.append(
                        self.make_collision_from_pixel(
                            horizontal_rgb, vertical_rgb,
                            x, y, now, rng
                        )
                    )

                glyphs = self.stream_glyphs(
                    streams, brightness_multiplier
                )
                for event in events:
                    glyphs.extend(
                        self.collision_glyphs(event, now, width)
                    )

                display = grid.copy()
                self.draw_glyphs(display, glyphs)
                write(display)
                last_glyphs = glyphs

                if f % 30 == 0:
                    self.update_status(
                        f"完成グリッド上のRGB移動: {f+1}/{motion_frames}"
                    )

            # ----------------------------------
            # 6. RGB文字を完全停止
            # ----------------------------------

            self.update_status(
                "RGBデータ静止中..."
            )

            # 最後のフレームで表示された文字だけ
            # 座標・文字内容・明るさを固定する
            frozen_glyphs = [
                dict(g) for g in last_glyphs
            ]

            frozen_frame = grid.copy()
            self.draw_glyphs(
                frozen_frame, frozen_glyphs
            )

            hold_frame(
                frozen_frame, freeze_seconds
            )

            # ----------------------------------
            # 6. 文字を個別にフェードアウト
            # ----------------------------------

            self.update_status(
                "RGBデータをフェードアウト中..."
            )

            # フェード開始のばらつきは0〜3秒
            # 各文字の消滅所要時間は1〜3秒
            fade_window = 3.0

            for glyph in frozen_glyphs:
                glyph["fade_start"] = float(
                    rng.uniform(0, fade_window)
                )
                glyph["fade_duration"] = float(
                    rng.uniform(1.0, 3.0)
                )

            fade_total = fade_window + 3.0
            fade_frames = math.ceil(
                fade_total * fps
            )

            for f in range(fade_frames):
                t = (f + 1) / fps
                display = grid.copy()

                for glyph in frozen_glyphs:
                    start = glyph["fade_start"]
                    duration = glyph["fade_duration"]

                    if t <= start:
                        factor = 1.0
                    elif t >= start + duration:
                        factor = 0.0
                    else:
                        p = (t - start) / duration
                        factor = 1 - self.smoothstep(p)

                    if factor <= 0:
                        continue

                    self.draw_text(
                        display,
                        glyph["text"],
                        glyph["x"],
                        glyph["y"],
                        alpha=glyph["alpha"] * factor,
                        scale=glyph["scale"],
                        brightness=glyph["brightness"]
                    )

                write(display)

            # ----------------------------------
            # 7. グリッドだけを表示
            # ----------------------------------

            hold_frame(grid, final)
            
            # v5 で追加
            # 動画の書き込みを完了させる
            writer.release()
            writer = None

            if instagram_mode:
                self.update_status(
                    "Instagram用にH.264変換中..."
                )

                self.convert_instagram(
                    temporary_output,
                    final_output
                )

            output = final_output
            #----------- ここまで

            elapsed = time.time() - clock

            self.update_status(
                "動画作成完了！"
            )

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

            if temporary_output is not None:
                try:
                    os.remove(temporary_output)
                except OSError:
                    pass

            self._ui_queue.put(("finished", None))

