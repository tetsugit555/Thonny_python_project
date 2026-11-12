"""BMP -> RGB配列、平均色、ストライプ画像。RGB順のuint8を扱う。"""
from dataclasses import dataclass
from PIL import Image
import numpy as np

@dataclass
class BMPAnalysis:
    rgb: np.ndarray
    width: int
    height: int
    row_colors: np.ndarray
    col_colors: np.ndarray

def analyze_bmp(path: str) -> BMPAnalysis:
    with Image.open(path) as img:
        rgb = np.array(img.convert("RGB"))
    height, width = rgb.shape[:2]
    row_colors = np.rint(rgb.mean(axis=1)).astype(np.uint8)
    col_colors = np.rint(rgb.mean(axis=0)).astype(np.uint8)
    return BMPAnalysis(rgb, width, height, row_colors, col_colors)
