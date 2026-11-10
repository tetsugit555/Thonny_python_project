
from PIL import Image
from tkinter import Tk, filedialog
from pathlib import Path

root = Tk()
root.withdraw()

# 元画像を選択
path = filedialog.askopenfilename(
    title="アイコンにする画像を選択",
    filetypes=[
        ("画像ファイル", "*.bmp *.png *.jpg *.jpeg")
    ]
)

if not path:
    raise SystemExit

img = Image.open(path).convert("RGBA")

# 正方形に中央トリミング
w, h = img.size
side = min(w, h)

left = (w - side) // 2
top = (h - side) // 2

img = img.crop((
    left, top,
    left + side, top + side
))

# 256×256に縮小
img = img.resize(
    (256, 256),
    Image.Resampling.LANCZOS
)

# ICO形式で保存
output = Path(path).with_suffix(".ico")

img.save(
    output,
    format="ICO",
    sizes=[
        (16, 16),
        (32, 32),
        (48, 48),
        (64, 64),
        (128, 128),
        (256, 256)
    ]
)

print("ICO作成完了:", output)
