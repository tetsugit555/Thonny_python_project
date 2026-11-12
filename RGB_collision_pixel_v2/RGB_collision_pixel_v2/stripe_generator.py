"""RGBの平均色から横・縦ストライプを作る。"""
import numpy as np
from bmp_analyzer import BMPAnalysis

def create_stripes(data: BMPAnalysis) -> tuple[np.ndarray, np.ndarray]:
    horizontal = np.broadcast_to(data.row_colors[:, None, :], data.rgb.shape).copy()
    vertical = np.broadcast_to(data.col_colors[None, :, :], data.rgb.shape).copy()
    return horizontal, vertical
