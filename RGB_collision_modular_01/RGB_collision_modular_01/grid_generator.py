"""RGB合成の計算。比較(明)と差の絶対値は異なる演算。"""
import numpy as np

def blend_lighten(horizontal: np.ndarray, vertical: np.ndarray) -> np.ndarray:
    """Photoshop比較(明)相当: RGB各チャンネルの最大値。"""
    return np.maximum(horizontal, vertical)

def difference_grid(horizontal: np.ndarray, vertical: np.ndarray) -> np.ndarray:
    """差の絶対値: |横RGB - 縦RGB|。uint8の減算オーバーフローを避ける。"""
    return np.abs(horizontal.astype(np.int16) - vertical.astype(np.int16)).astype(np.uint8)
