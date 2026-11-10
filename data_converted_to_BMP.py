
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
from pathlib import Path

# ダイアログ用のウィンドウ
root = tk.Tk()
root.withdraw()

# 1. RGBテキストファイルを選択
txt_path = filedialog.askopenfilename(
    title="RGBテキストファイルを選択",
    filetypes=[
        ("テキストファイル", "*.txt"),
        ("すべてのファイル", "*.*")
    ]
)

if txt_path:
    try:
        # テキストを読み込む
        with open(txt_path, "r", encoding="utf-8-sig") as f:
            lines = [
                line.split()
                for line in f
                if line.strip()
            ]

        if not lines:
            raise ValueError("RGBデータがありません")

        # 画像サイズを自動判定
        height = len(lines)
        width = len(lines[0])

        # 各行の画素数をチェック
        for y, row in enumerate(lines):
            if len(row) != width:
                raise ValueError(
                    f"{y + 1}行目の画素数が一致しません"
                )

        # RGBデータを復元
        pixels = []

        for row in lines:
            for value in row:
                if len(value) != 6:
                    raise ValueError(
                        f"不正なRGB値: {value}"
                    )

                r = int(value[0:2], 16)
                g = int(value[2:4], 16)
                b = int(value[4:6], 16)

                pixels.append((r, g, b))

        # BMP画像を作成
        img = Image.new("RGB", (width, height))
        img.putdata(pixels)

        # 2. BMPの保存先を選択
        default_name = Path(txt_path).stem + "_restored.bmp"

        save_path = filedialog.asksaveasfilename(
            title="BMP画像の保存先を指定",
            defaultextension=".bmp",
            initialfile=default_name,
            filetypes=[
                ("BMP画像", "*.bmp")
            ]
        )

        if save_path:
            img.save(save_path, format="BMP")

            messagebox.showinfo(
                "復元成功",
                f"BMP画像を保存しました！\n\n"
                f"幅: {width} px\n"
                f"高さ: {height} px\n"
                f"画素数: {width * height:,}\n\n"
                f"{save_path}"
            )

            print("BMP復元成功！")
            print(f"画像サイズ: {width} x {height}")
            print(f"画素数: {width * height:,}")
            print(f"保存先: {save_path}")

    except Exception as e:
        messagebox.showerror(
            "エラー",
            str(e)
        )

root.destroy()