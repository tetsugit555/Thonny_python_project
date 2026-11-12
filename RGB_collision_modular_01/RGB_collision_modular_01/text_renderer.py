import cv2
import numpy as np

class TextRendererMixin:
    def rgb_text(self, color):
        r, g, b = [int(v) for v in color]

        if self.data_format.get() == "hex":
            return f"#{r:02X}{g:02X}{b:02X}"

        return f"({r},{g},{b})"

    def calculate_font_scale(self, height):
        (_, reference_height), _ = cv2.getTextSize(
            "RGB0123456789",
            self.FONT, 1.0, 1
        )
        return (
            height / 100.0
        ) / max(1, reference_height)

    def text_width(self, text, scale):
        (w, _), _ = cv2.getTextSize(
            text, self.FONT, scale, 1
        )
        return w

    @staticmethod
    def smoothstep(p):
        p = max(0.0, min(1.0, p))
        return p * p * (3 - 2 * p)

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

        alpha = float(np.clip(alpha, 0, 1))

        cv2.addWeighted(
            overlay, alpha,
            roi, 1 - alpha,
            0, roi
        )

    def draw_glyphs(self, frame, glyphs):
        for glyph in glyphs:
            self.draw_text(
                frame,
                glyph["text"],
                glyph["x"],
                glyph["y"],
                alpha=glyph["alpha"],
                scale=glyph["scale"],
                brightness=glyph["brightness"]
            )

