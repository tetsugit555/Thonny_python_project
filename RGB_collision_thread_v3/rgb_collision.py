import numpy as np

def collision_at_pixel(horizontal_rgb, vertical_rgb, x, y):
    """同じ(x,y)の横・縦RGBと差の絶対値を返す。入力はRGB順。"""
    if horizontal_rgb.shape != vertical_rgb.shape or horizontal_rgb.ndim != 3 or horizontal_rgb.shape[2] != 3:
        raise ValueError("横・縦ストライプは同じ(H,W,3)形状が必要です")
    height, width = horizontal_rgb.shape[:2]
    if not (0 <= x < width and 0 <= y < height):
        raise IndexError("座標が画像範囲外です")
    a = horizontal_rgb[y, x].copy()
    b = vertical_rgb[y, x].copy()
    d = np.abs(a.astype(np.int16) - b.astype(np.int16)).astype(np.uint8)
    return a, b, d


class RGBCollisionMixin:
    def make_collision_from_pixel(self, horizontal_rgb, vertical_rgb, x, y, now, rng):
        """指定座標の2色を取り出し、既存の衝突アニメーションイベントを生成する。"""
        a, b, d = collision_at_pixel(horizontal_rgb, vertical_rgb, x, y)
        height, width = horizontal_rgb.shape[:2]
        return self.make_collision(x, y, now, a, b, d, width, height, rng)

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

        approach = float(rng.uniform(2.0, 4.0))
        fade_in = float(rng.uniform(0.6, 1.0))
        hold = 1.5
        fade_out = 0.7

        widths = [
            self.text_width(s, scale)
            for s in (a_text, b_text, d_text)
        ]

        margin = max(widths) / 2 + 3

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
            "total": approach + fade_in + hold + fade_out,
            "a_text": a_text,
            "b_text": b_text,
            "d_text": d_text,
            "scale": scale
        }

    def collision_glyphs(self, event, now, width):
        age = now - event["start"]

        if age < 0 or age >= event["total"]:
            return []

        cx = event["x"]
        cy = event["y"]
        scale = event["scale"]
        approach = event["approach"]

        a = event["a_text"]
        b = event["b_text"]
        d = event["d_text"]

        wa = self.text_width(a, scale)
        wb = self.text_width(b, scale)
        wd = self.text_width(d, scale)

        if age < approach:
            p = self.smoothstep(age / approach)

            lx = (
                -wa - 5
                + (cx + wa / 2 + 5) * p
            )

            rx = (
                width + 5
                + (cx - wb / 2 - width - 5) * p
            )

            if p < 0.60:
                alpha = 0.78
            else:
                alpha = 0.78 * (
                    1 - self.smoothstep(
                        (p - 0.60) / 0.40
                    )
                )

            return [
                {
                    "text": a, "x": lx, "y": cy,
                    "scale": scale,
                    "brightness": 230,
                    "alpha": alpha
                },
                {
                    "text": b, "x": rx, "y": cy,
                    "scale": scale,
                    "brightness": 230,
                    "alpha": alpha
                }
            ]

        p = age - approach

        fade_in = event["fade_in"]
        hold = event["hold"]
        fade_out = event["fade_out"]

        if p < fade_in:
            alpha = self.smoothstep(
                p / fade_in
            ) * 0.88
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
            1.0, p / (
                fade_in + hold + fade_out
            )
        ) * self.image_height * 0.012

        return [{
            "text": d,
            "x": cx - wd / 2,
            "y": cy - drift,
            "scale": scale,
            "brightness": 240,
            "alpha": alpha
        }]

