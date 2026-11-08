
from PIL import Image, ImageChops
from tkinter import Tk, filedialog

root = Tk()
root.withdraw()

# 画像を2枚選択
file1 = filedialog.askopenfilename(title="画像Aを選択")
file2 = filedialog.askopenfilename(title="画像Bを選択")

if file1 and file2:
    img1 = Image.open(file1).convert("RGB")
    img2 = Image.open(file2).convert("RGB")

    # 画像Bを画像Aと同じサイズにする
    img2 = img2.resize(img1.size)

    # RGB各チャンネルの差の絶対値
    result = ImageChops.difference(img1, img2)

    # 新しい画像を保存
    result.save("difference.png")
    result.show()

    print("difference.png を保存しました")

root.destroy()
