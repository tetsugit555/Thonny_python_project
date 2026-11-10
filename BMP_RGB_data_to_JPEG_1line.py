
from PIL import Image, ImageDraw, ImageFont
from tkinter import Tk, filedialog, messagebox
from pathlib import Path
import math

# ===== A2 横・300dpi =====
DPI = 300
WIDTH = round(594 / 25.4 * DPI)
HEIGHT = round(420 / 25.4 * DPI)
MARGIN = round(15 / 25.4 * DPI)
LINE_SPACING = 1.15

# ===== フォントを探す =====
FONT_PATHS = [
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/cour.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
]

def get_font(size):
    for path in FONT_PATHS:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass
    raise RuntimeError("等幅フォントが見つかりません")

# ===== 最初の1行を読み込む =====
def read_first_row(filename):
    with open(filename, "r", encoding="utf-8-sig") as f:
        line = f.readline()

    values = line.strip().split()

    if not values:
        raise ValueError("最初の行にデータがありません")

    for value in values:
        if len(value) != 6:
            raise ValueError("RGBが6桁ではありません: " + value)
        try:
            int(value, 16)
        except ValueError:
            raise ValueError("不正なRGB値: " + value)

    return values

# ===== 配置を計算 =====
def calculate_layout(values, size):
    font = get_font(size)
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    # 等幅フォントの文字幅
    char_width = draw.textlength("0", font=font)
    line_height = math.ceil(size * LINE_SPACING)

    usable_width = WIDTH - 2 * MARGIN
    usable_height = HEIGHT - 2 * MARGIN

    # RGB 6文字 + 区切りスペース1文字
    chars_per_line = math.floor(usable_width / char_width)
    rgb_per_line = (chars_per_line + 1) // 7

    if rgb_per_line < 1:
        return None

    rows = math.ceil(len(values) / rgb_per_line)

    if rows * line_height > usable_height:
        return None

    return font, rgb_per_line, rows, line_height

# ===== メイン処理 =====
def main():
    root = Tk()
    root.withdraw()

    input_file = filedialog.askopenfilename(
        title="RGBテキストを選択",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )

    if not input_file:
        root.destroy()
        return

    try:
        values = read_first_row(input_file)

        print("RGBデータ数:", len(values))
        print("A2画像:", WIDTH, "x", HEIGHT)

        # 最大フォントサイズを探す
        best = None
        best_size = 0

        for size in range(1, 301):
            layout = calculate_layout(values, size)
            if layout is not None:
                best = layout
                best_size = size

        if best is None:
            raise ValueError("A2に収まりません")

        font, rgb_per_line, rows, line_height = best

        print("フォントサイズ:", best_size, "px")
        print("1行のRGB数:", rgb_per_line)
        print("行数:", rows)

        output_file = filedialog.asksaveasfilename(
            title="JPEG保存先",
            defaultextension=".jpg",
            initialfile=Path(input_file).stem + "_A2.jpg",
            filetypes=[("JPEG", "*.jpg")]
        )

        if not output_file:
            root.destroy()
            return

        # ===== 画像作成 =====
        img = Image.new("RGB", (WIDTH, HEIGHT), "white")
        draw = ImageDraw.Draw(img)

        total_height = rows * line_height
        y = (HEIGHT - total_height) // 2

        for i in range(rows):
            start = i * rgb_per_line
            end = start + rgb_per_line

            line = " ".join(values[start:end])

            # 各行を中央揃え
            #line_width = draw.textlength(line, font=font)
            #x = (WIDTH - line_width) / 2
            
            #左揃え
            x = MARGIN

            draw.text(
                (x, y),
                line,
                font=font,
                fill="black",
                anchor="lt"
            )

            y += line_height

        img.save(
            output_file,
            "JPEG",
            quality=100,
            subsampling=0,
            dpi=(DPI, DPI)
        )

        print("保存完了:", output_file)
        messagebox.showinfo(
            "完成",
            f"A2 JPEGを保存しました。\n"
            f"RGB数: {len(values)}\n"
            f"フォント: {best_size}px\n"
            f"配置: {rgb_per_line}組 × {rows}行"
        )

    except Exception as e:
        messagebox.showerror("エラー", str(e))
        print("エラー:", e)

    finally:
        root.destroy()

if __name__ == "__main__":
    main()
