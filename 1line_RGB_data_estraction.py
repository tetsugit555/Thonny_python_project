
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
from pathlib import Path

# --------------------------------------------------
# BMP RGB抽出ツール
# --------------------------------------------------

root = tk.Tk()
root.withdraw()

# 1. BMPファイル選択
bmp_path = filedialog.askopenfilename(
    title="BMPファイルを選択",
    filetypes=[("BMP画像", "*.bmp")]
)

if not bmp_path:
    root.destroy()
    raise SystemExit

try:
    img = Image.open(bmp_path)
    if img.format != "BMP":
        raise ValueError("BMPファイルではありません")
    img = img.convert("RGB")
except Exception as e:
    messagebox.showerror("エラー", str(e))
    root.destroy()
    raise SystemExit

width, height = img.size

root.deiconify()
root.title("BMP RGB 一列抽出ツール")
root.geometry("540x410")
root.resizable(False, False)

# 変数
direction = tk.StringVar(value="horizontal")
position = tk.IntVar(value=height // 2)
save_path = tk.StringVar()

# 画像情報
tk.Label(
    root,
    text=f"画像サイズ：{width} × {height} px",
    font=("Arial", 12, "bold")
).pack(pady=15)

tk.Label(
    root,
    text=Path(bmp_path).name
).pack()

# 2. 抽出方向選択
frame_direction = tk.LabelFrame(
    root, text="抽出方向", padx=15, pady=10
)
frame_direction.pack(fill="x", padx=20, pady=15)

def update_direction():
    if direction.get() == "horizontal":
        maximum = height - 1
        axis = "Y"
    else:
        maximum = width - 1
        axis = "X"

    scale.config(to=maximum)
    position.set(maximum // 2)
    axis_label.config(text=f"{axis}座標：{position.get()} px")

tk.Radiobutton(
    frame_direction,
    text="横方向（左 → 右）",
    variable=direction,
    value="horizontal",
    command=update_direction
).pack(anchor="w")

tk.Radiobutton(
    frame_direction,
    text="縦方向（上 → 下）",
    variable=direction,
    value="vertical",
    command=update_direction
).pack(anchor="w")

# スライダー
frame_position = tk.LabelFrame(
    root, text="抽出位置", padx=15, pady=10
)
frame_position.pack(fill="x", padx=20)

axis_label = tk.Label(frame_position, text="")
axis_label.pack()

def update_position(value):
    axis = "Y" if direction.get() == "horizontal" else "X"
    axis_label.config(text=f"{axis}座標：{int(float(value))} px")

scale = tk.Scale(
    frame_position,
    from_=0,
    to=height - 1,
    orient="horizontal",
    variable=position,
    command=update_position,
    resolution=1,
    length=460
)
scale.pack()

update_direction()

# 3. 保存場所設定
def select_save():
    path = filedialog.asksaveasfilename(
        title="RGBデータの保存先",
        defaultextension=".txt",
        filetypes=[("テキストファイル", "*.txt")],
        initialfile=Path(bmp_path).stem + "_RGB.txt"
    )
    if path:
        save_path.set(path)
        save_label.config(text=Path(path).name)

tk.Button(
    root,
    text="TXT保存先を選択",
    command=select_save
).pack(pady=(15, 5))

save_label = tk.Label(
    root,
    text="保存先未設定",
    fg="gray"
)
save_label.pack()

# 4. GO
def extract_rgb():
    if not save_path.get():
        messagebox.showwarning(
            "保存先未設定",
            "先にTXT保存先を選択してください"
        )
        return

    pos = position.get()

    try:
        with open(save_path.get(), "w", encoding="utf-8") as f:
            if direction.get() == "horizontal":
                for x in range(width):
                    r, g, b = img.getpixel((x, pos))
                    f.write(f"{r:03d},{g:03d},{b:03d}\n")
                count = width
            else:
                for y in range(height):
                    r, g, b = img.getpixel((pos, y))
                    f.write(f"{r:03d},{g:03d},{b:03d}\n")
                count = height

        messagebox.showinfo(
            "抽出完了",
            f"{count}ピクセル分のRGBデータを保存しました。"
        )
    except Exception as e:
        messagebox.showerror("エラー", str(e))

tk.Button(
    root,
    text="GO － RGB抽出",
    font=("Arial", 12, "bold"),
    width=22,
    height=2,
    command=extract_rgb
).pack(pady=18)

root.mainloop()
