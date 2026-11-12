import numpy as np

class StripeMotionMixin:
    def make_motion(self, count, duration, rng):
        starts = rng.uniform(
            0, duration * 0.55, size=count
        )
        travel = (
            duration - starts
        ) * rng.uniform(
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

