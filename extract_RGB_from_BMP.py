
from pathlib import Path
import struct
import tkinter as tk
from tkinter import filedialog, messagebox


def extract_bmp_rgb(data):
    # BMPファイル確認
    if data[:2] != b"BM":
        raise ValueError("BMPファイルではありません")

    # BMPヘッダー情報
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
        raise ValueError(
            "24bit・無圧縮BMPのみ対応しています\n"
            f"bit数: {bit_count}, 圧縮形式: {compression}"
        )

    # BMPは1行を4バイト単位に揃える
    row_size = ((width * 3 + 3) // 4) * 4

    image_height = abs(height)

    if pixel_offset + row_size * image_height > len(data):
        raise ValueError("画像データが途中で切れています")

    rgb_data = bytearray()

    # 上から下、左から右の順に並べ直す
    for y in range(image_height):
        if height > 0:
            bmp_y = image_height - 1 - y
        else:
            bmp_y = y

        row_start = pixel_offset + bmp_y * row_size

        for x in range(width):
            pos = row_start + x * 3

            b = data[pos]
            g = data[pos + 1]
            r = data[pos + 2]

            rgb_data.extend((r, g, b))

    return width, image_height, rgb_data


def main():
    root = tk.Tk()
    root.withdraw()

    # BMPファイルを選択
    input_file = filedialog.askopenfilename(
        title="BMP画像を選択",
        filetypes=[
            ("BMP画像", "*.bmp"),
            ("すべてのファイル", "*.*")
        ]
    )

    if not input_file:
        root.destroy()
        return

    # 保存先フォルダを選択
    output_folder = filedialog.askdirectory(
        title="テキストの保存先フォルダを選択"
    )

    if not output_folder:
        root.destroy()
        return

    try:
        data = Path(input_file).read_bytes()

        width, height, rgb_data = extract_bmp_rgb(data)

        output_file = (
            Path(output_folder)
            / (Path(input_file).stem + "_RGB.txt")
        )

        # 1ピクセル = RRGGBB
        # 画像と同じ行構造で保存
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
            f"保存しました！\n\n"
            f"{output_file}\n\n"
            f"画像サイズ: {width} x {height}\n"
            f"画素数: {width * height:,}\n"
            f"RGBデータ: {len(rgb_data):,} bytes"
        )

    except Exception as e:
        messagebox.showerror("エラー", str(e))

    finally:
        root.destroy()


if __name__ == "__main__":
    main()
