
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


def extract_jpeg_scan_data(data):
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("JPEGファイルではありません")

    result = bytearray()
    pos = 2

    while pos < len(data):
        if data[pos] != 0xFF:
            raise ValueError("JPEGの構造が不正です")

        # マーカー前のFF埋め草をスキップ
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1

        if pos >= len(data):
            raise ValueError("不完全なJPEGです")

        marker = data[pos]
        pos += 1

        if marker == 0xD9:  # EOI
            return bytes(result)

        # 長さフィールドのないマーカー
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue

        if pos + 2 > len(data):
            raise ValueError("不完全なJPEGセグメントです")

        length = int.from_bytes(data[pos:pos+2], "big")

        if length < 2 or pos + length > len(data):
            raise ValueError("JPEGセグメント長が不正です")

        if marker != 0xDA:  # SOS以外は飛ばす
            pos += length
            continue

        # SOSヘッダーを飛ばして圧縮データへ
        pos += length
        start = pos

        while pos < len(data):
            if data[pos] != 0xFF:
                pos += 1
                continue

            if pos + 1 >= len(data):
                raise ValueError("圧縮データが途中で終了")

            next_byte = data[pos + 1]

            if next_byte == 0x00:  # FF 00 はデータ
                pos += 2
                continue

            if next_byte == 0xFF:  # FF埋め草
                pos += 1
                continue

            if 0xD0 <= next_byte <= 0xD7:
                # リスタートマーカーは除外
                result.extend(data[start:pos])
                pos += 2
                start = pos
                continue

            # 次のJPEGマーカーに到達
            result.extend(data[start:pos])
            break
        else:
            raise ValueError("EOIマーカーがありません")

    raise ValueError("JPEGの終了マーカーがありません")


def main():
    root = tk.Tk()
    root.withdraw()

    # JPEGファイル選択
    input_file = filedialog.askopenfilename(
        title="JPEG画像を選択",
        filetypes=[
            ("JPEG画像", "*.jpg *.jpeg"),
            ("すべてのファイル", "*.*")
        ]
    )

    if not input_file:
        root.destroy()
        return

    # 保存フォルダ選択
    output_folder = filedialog.askdirectory(
        title="テキストの保存先フォルダを選択"
    )

    if not output_folder:
        root.destroy()
        return

    try:
        data = Path(input_file).read_bytes()
        image_data = extract_jpeg_scan_data(data)

        if not image_data:
            raise ValueError("圧縮画像データが見つかりません")

        output_file = (
            Path(output_folder)
            / (Path(input_file).stem + "_data.txt")
        )

        # 1行16バイト、16進数で保存
        with output_file.open("w", encoding="ascii") as f:
            for i in range(0, len(image_data), 16):
                chunk = image_data[i:i+16]
                f.write(chunk.hex(" ").upper() + "\n")

        messagebox.showinfo(
            "変換完了",
            f"保存しました！\n\n"
            f"{output_file}\n\n"
            f"抽出データ: {len(image_data):,} bytes"
        )

    except Exception as e:
        messagebox.showerror("エラー", str(e))

    finally:
        root.destroy()


if __name__ == "__main__":
    main()
