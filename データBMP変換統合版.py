
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image
import struct


# ==========================================
# BMP → RGB TXT
# ==========================================

def extract_bmp_rgb(data):
    if data[:2] != b"BM":
        raise ValueError("BMPファイルではありません")

    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]

    if dib_size < 40:
        raise ValueError("このBMP形式には対応していません")

    width = struct.unpack_from("<i", data, 18)[0]
    height = struct.unpack_from("<i", data, 22)[0]
    planes = struct.unpack_from("<H", data, 26)[0]
    bit_count = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]

    if width <= 0 or height == 0:
        raise ValueError("画像サイズが不正です")

    if planes != 1 or bit_count != 24 or compression != 0:
        raise ValueError("24bit・無圧縮BMPのみ対応しています")

    row_size = ((width * 3 + 3) // 4) * 4
    image_height = abs(height)

    if pixel_offset + row_size * image_height > len(data):
        raise ValueError("画像データが途中で切れています")

    rgb_data = bytearray()

    for y in range(image_height):
        bmp_y = image_height - 1 - y if height > 0 else y
        row_start = pixel_offset + bmp_y * row_size

        for x in range(width):
            pos = row_start + x * 3

            b = data[pos]
            g = data[pos + 1]
            r = data[pos + 2]

            rgb_data.extend((r, g, b))

    return width, image_height, rgb_data


def bmp_to_txt():
    input_file = filedialog.askopenfilename(
        title="BMP画像を選択",
        filetypes=[("BMP画像", "*.bmp")]
    )

    if not input_file:
        return

    output_folder = filedialog.askdirectory(
        title="RGBテキストの保存先フォルダを選択"
    )

    if not output_folder:
        return

    try:
        data = Path(input_file).read_bytes()
        width, height, rgb_data = extract_bmp_rgb(data)

        output_file = (
            Path(output_folder)
            / (Path(input_file).stem + "_RGB.txt")
        )

        with output_file.open("w", encoding="ascii") as f:
            for y in range(height):
                start = y * width * 3
                end = start + width * 3
                row = rgb_data[start:end]

                colors = [
                    row[i:i+3].hex().upper()
                    for i in range(0, len(row), 3)
                ]

                f.write(" ".join(colors) + "\n")

        messagebox.showinfo(
            "変換完了",
            f"BMP → TXT 完了！\n\n"
            f"画像サイズ: {width} x {height}\n"
            f"画素数: {width * height:,}\n\n"
            f"保存先:\n{output_file}"
        )

    except Exception as e:
        messagebox.showerror("エラー", str(e))


# ==========================================
# RGB TXT → BMP
# ==========================================

def txt_to_bmp():
    input_file = filedialog.askopenfilename(
        title="RGBテキストファイルを選択",
        filetypes=[("テキストファイル", "*.txt")]
    )

    if not input_file:
        return

    output_folder = filedialog.askdirectory(
        title="BMP画像の保存先フォルダを選択"
    )

    if not output_folder:
        return

    try:
        with open(input_file, "r", encoding="utf-8-sig") as f:
            lines = [
                line.split()
                for line in f
                if line.strip()
            ]

        if not lines:
            raise ValueError("RGBデータがありません")

        height = len(lines)
        width = len(lines[0])

        pixels = []

        for y, row in enumerate(lines):
            if len(row) != width:
                raise ValueError(
                    f"{y + 1}行目の画素数が一致しません"
                )

            for value in row:
                if len(value) != 6:
                    raise ValueError(
                        f"不正なRGB値: {value}"
                    )

                try:
                    r = int(value[0:2], 16)
                    g = int(value[2:4], 16)
                    b = int(value[4:6], 16)
                except ValueError:
                    raise ValueError(
                        f"不正な16進数: {value}"
                    )

                pixels.append((r, g, b))

        img = Image.new("RGB", (width, height))
        img.putdata(pixels)

        output_file = (
            Path(output_folder)
            / (Path(input_file).stem + "_restored.bmp")
        )

        img.save(output_file, format="BMP")

        messagebox.showinfo(
            "復元完了",
            f"TXT → BMP 完了！\n\n"
            f"画像サイズ: {width} x {height}\n"
            f"画素数: {width * height:,}\n\n"
            f"保存先:\n{output_file}"
        )

    except Exception as e:
        messagebox.showerror("エラー", str(e))


# ==========================================
# メインウィンドウ
# ==========================================

root = tk.Tk()
root.title("BMP ⇔ RGB TXT Converter")
root.geometry("420x250")
root.resizable(False, False)

tk.Label(
    root,
    text="BMP ⇔ RGB TXT Converter",
    font=("Arial", 16, "bold")
).pack(pady=(25, 12))

tk.Label(
    root,
    text="変換方向を選択してください",
    font=("Arial", 10)
).pack(pady=(0, 15))

tk.Button(
    root,
    text="BMP → RGB TXT",
    font=("Arial", 12),
    width=25,
    command=bmp_to_txt
).pack(pady=5)

tk.Button(
    root,
    text="RGB TXT → BMP",
    font=("Arial", 12),
    width=25,
    command=txt_to_bmp
).pack(pady=5)

root.mainloop()
