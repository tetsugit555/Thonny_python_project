
from PIL import Image
from tkinter import Tk, filedialog, messagebox
from pathlib import Path

root = Tk()
root.withdraw()

# JPEGファイルを選択
input_path = filedialog.askopenfilename(
    title="変換するJPEGを選択",
    filetypes=[
        ("JPEG画像", "*.jpg *.jpeg"),
        ("すべてのファイル", "*.*")
    ]
)

if input_path:
    # BMPの保存先を指定
    output_path = filedialog.asksaveasfilename(
        title="BMPの保存先を指定",
        defaultextension=".bmp",
        initialfile=Path(input_path).stem + ".bmp",
        filetypes=[("BMP画像", "*.bmp")]
    )

    if output_path:
        try:
            with Image.open(input_path) as img:
                # 24bit RGBに変換
                rgb = img.convert("RGB")
                rgb.save(output_path, format="BMP")

                width, height = rgb.size

            print("変換完了！")
            print(f"サイズ: {width} × {height}")
            print(f"画素数: {width * height:,}")
            print(f"保存先: {output_path}")

            #messagebox.showinfo(
            #    "変換完了",
            #    f"BMPを保存しました。\n{output_path}"
            #)

        except Exception as e:
            messagebox.showerror("エラー", str(e))

 #root.destroy()


