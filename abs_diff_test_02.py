
from PIL import Image, ImageChops
from tkinter import Tk, filedialog

root = Tk()
root.withdraw()

# 画像Aを選択
file1 = filedialog.askopenfilename(
    title="画像Aを選択"
)

# 画像Bを選択
file2 = filedialog.askopenfilename(
    title="画像Bを選択"
)

if file1 and file2:
    with Image.open(file1) as source1:
        img1 = source1.convert("RGB")
    with Image.open(file2) as source2:
        img2 = source2.convert("RGB")

    # 画像BをAと同じサイズにする
    img2 = img2.resize(img1.size)

    # 差の絶対値を計算
    result = ImageChops.difference(img1, img2)

    # 保存先を選択
    save_path = filedialog.asksaveasfilename(
        title="生成画像の保存先を選択",
        defaultextension=".png",
        initialfile="difference.png",
        filetypes=[
            ("PNG画像", "*.png"),
            ("TIFF画像", "*.tif"),
            ("JPEG画像", "*.jpg")
        ]
    )

    if save_path:
        result.save(save_path)
        result.show()
        print("保存完了:", save_path)
    else:
        print("保存をキャンセルしました")

root.destroy()
