
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from pathlib import Path

# ==========================================
# BMP RGB 一列抽出ツール
# 画像プレビュー・抽出位置表示付き
# ==========================================

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
    with Image.open(bmp_path) as source:
        if source.format != "BMP":
            raise ValueError("BMPファイルではありません")
        img = source.convert("RGB")
except Exception as e:
    messagebox.showerror("エラー", str(e))
    root.destroy()
    raise SystemExit

width, height = img.size

# プレビュー画像を作成
preview = img.copy()
preview.thumbnail((650, 380), Image.Resampling.LANCZOS)

preview_width, preview_height = preview.size
preview_photo = ImageTk.PhotoImage(preview)

# メインウィンドウ
root.deiconify()
root.title("BMP RGB 一列抽出ツール")
root.geometry("740x900")
root.resizable(True, True)

direction = tk.StringVar(value="horizontal")
position = tk.IntVar(value=(height - 1) // 2)
save_path = tk.StringVar()

# 画像情報
tk.Label(
    root,
    text=f"画像サイズ：{width} × {height} px",
    font=("Arial", 12, "bold")
).pack(pady=(12, 5))

tk.Label(
    root,
    text=Path(bmp_path).name
).pack()

# 2. 抽出方向
direction_frame = tk.LabelFrame(
    root, text="抽出方向", padx=12, pady=8
)
direction_frame.pack(fill="x", padx=20, pady=10)

def update_direction():
    if direction.get() == "horizontal":
        maximum = height - 1
    else:
        maximum = width - 1

    scale.config(to=maximum)
    position.set(maximum // 2)
    update_preview()

tk.Radiobutton(
    direction_frame,
    text="横方向（左 → 右）",
    variable=direction,
    value="horizontal",
    command=update_direction
).pack(anchor="w")

tk.Radiobutton(
    direction_frame,
    text="縦方向（上 → 下）",
    variable=direction,
    value="vertical",
    command=update_direction
).pack(anchor="w")

# 3. 抽出位置
position_frame = tk.LabelFrame(
    root, text="抽出位置", padx=12, pady=8
)
position_frame.pack(fill="x", padx=20)

axis_label = tk.Label(position_frame)
axis_label.pack()

def update_preview(value=None):
    pos = position.get()

    if direction.get() == "horizontal":
        axis_label.config(text=f"Y座標：{pos} px")
        line_y = (
            pos * (preview_height - 1) / max(1, height - 1)
        )
        canvas.coords(
            guide_line,
            0, line_y, preview_width, line_y
        )
    else:
        axis_label.config(text=f"X座標：{pos} px")
        line_x = (
            pos * (preview_width - 1) / max(1, width - 1)
        )
        canvas.coords(
            guide_line,
            line_x, 0, line_x, preview_height
        )

scale = tk.Scale(
    position_frame,
    from_=0,
    to=height - 1,
    orient="horizontal",
    variable=position,
    command=update_preview,
    resolution=1,
    length=650
)
scale.pack()

# 4. 元画像プレビュー
preview_frame = tk.LabelFrame(
    root,
    text="元画像プレビュー（クリックでも位置指定可能）",
    padx=10,
    pady=10
)
preview_frame.pack(padx=20, pady=10)

canvas = tk.Canvas(
    preview_frame,
    width=preview_width,
    height=preview_height,
    highlightthickness=0
)
canvas.pack()

canvas.create_image(
    0, 0,
    anchor="nw",
    image=preview_photo
)

guide_line = canvas.create_line(
    0, 0, preview_width, 0,
    fill="red",
    width=2
)

# プレビュー画像クリック
def click_preview(event):
    if direction.get() == "horizontal":
        if preview_height <= 1:
            pos = 0
        else:
            pos = round(
                event.y * (height - 1)
                / (preview_height - 1)
            )
        pos = max(0, min(height - 1, pos))
    else:
        if preview_width <= 1:
            pos = 0
        else:
            pos = round(
                event.x * (width - 1)
                / (preview_width - 1)
            )
        pos = max(0, min(width - 1, pos))

    position.set(pos)
    update_preview()

canvas.bind("<Button-1>", click_preview)

update_preview()

# 5. 保存先設定
def select_save():
    path = filedialog.asksaveasfilename(
        title="RGBデータの保存先",
        defaultextension=".txt",
        filetypes=[("テキストファイル", "*.txt")],
        initialfile=(
            Path(bmp_path).stem + "_RGB.txt"
        )
    )

    if path:
        save_path.set(path)
        save_label.config(
            text=str(path),
            fg="black"
        )

tk.Button(
    root,
    text="TXT保存先を選択",
    command=select_save
).pack(pady=(10, 5))

save_label = tk.Label(
    root,
    text="保存先未設定",
    fg="gray",
    wraplength=650
)
save_label.pack()

# 6. RGB抽出
def extract_rgb():
    if not save_path.get():
        messagebox.showwarning(
            "保存先未設定",
            "先にTXT保存先を選択してください"
        )
        return

    pos = position.get()

    try:
        with open(
            save_path.get(), "w", encoding="utf-8"
        ) as f:

            if direction.get() == "horizontal":
                for x in range(width):
                    r, g, b = img.getpixel((x, pos))
                    f.write(
                        f"{r:03d},{g:03d},{b:03d}\n"
                    )
                count = width

            else:
                for y in range(height):
                    r, g, b = img.getpixel((pos, y))
                    f.write(
                        f"{r:03d},{g:03d},{b:03d}\n"
                    )
                count = height

        messagebox.showinfo(
            "抽出完了",
            f"{count}ピクセル分のRGBデータを保存しました。\n"
            f"抽出位置：{pos} px"
        )

    except Exception as e:
        messagebox.showerror("エラー", str(e))

tk.Button(
    root,
    text="GO － RGB抽出",
    font=("Arial", 12, "bold"),
    width=24,
    height=2,
    command=extract_rgb
).pack(pady=15)

root.mainloop()
