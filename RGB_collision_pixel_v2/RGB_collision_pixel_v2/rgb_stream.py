import numpy as np

class RGBStreamMixin:
    def make_stream(
        self, width, height, rng, palette,
        direction=None, entering=False
    ):
        depth = float(rng.uniform(0.25, 1.0))

        scale = self.base_scale * (
            0.65 + 0.75 * depth
        )

        # ランダム速度を一度だけ決定
        base_speed = width * float(
            rng.uniform(0.012, 0.065)
        ) * (0.45 + 0.55 * depth)

        brightness = int(
            255 * (0.35 + 0.65 * depth)
        )

        alpha = float(
            rng.uniform(0.25, 0.75)
        )

        count = int(rng.integers(5, 14))

        texts = [
            self.rgb_text(
                palette[int(rng.integers(len(palette)))]
            )
            for _ in range(count)
        ]

        gap = height * float(
            rng.uniform(0.012, 0.05)
        )

        advance = max(
            self.text_width(s, scale)
            for s in texts
        ) + gap

        total = advance * count

        if direction is None:
            direction = int(rng.choice([-1, 1]))

        #if entering:
        #    x = -total if direction == 1 else width
        #else:
        #    x = float(rng.uniform(-total, width))
        
        #V5 で書き換え
        
                # RGBデータ列は必ず画面の外から登場する
        if direction == 1:
            x = -total
        else:
            x = width
        
        #---------- ここまで

        y = float(rng.uniform(
            max(10, height * 0.04),
            max(11, height * 0.96)
        ))

        return {
            "x": x,
            "y": y,
            "speed": base_speed,
            "direction": direction,
            "scale": scale,
            "brightness": brightness,
            "alpha": alpha,
            "texts": texts,
            "advance": advance,
            "total": total
        }

    def advance_streams(
        self, streams, dt,
        width, height, rng, palette,
        speed_multiplier
    ):
        for i, stream in enumerate(streams):

            # 速度倍率は全ストリーム共通
            # 個々の速度は途中で変化しない
            stream["x"] += (
                stream["speed"]
                * speed_multiplier
                * stream["direction"]
                * dt
            )

            x = stream["x"]

            exited = (
                stream["direction"] == 1
                and x > width
            ) or (
                stream["direction"] == -1
                and x + stream["total"] < 0
            )

            if exited:
                streams[i] = self.make_stream(
                    width, height, rng, palette,
                    direction=stream["direction"],
                    entering=True
                )

    def stream_glyphs(
        self, streams, brightness_multiplier
    ):
        glyphs = []

        for stream in streams:
            brightness = int(
                stream["brightness"]
                * brightness_multiplier
            )

            for j, text in enumerate(stream["texts"]):
                glyphs.append({
                    "text": text,
                    "x": (
                        stream["x"]
                        + j * stream["advance"]
                    ),
                    "y": stream["y"],
                    "scale": stream["scale"],
                    "brightness": brightness,
                    "alpha": stream["alpha"]
                })

        return glyphs

