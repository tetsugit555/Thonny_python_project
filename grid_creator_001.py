import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk, ImageChops

root = tk.Tk()
root.withdraw()
bmp_path = filedialog.askopenfilename(
    title='BMPファイルを選択', filetypes=[('BMP画像', '*.bmp')]
)
if not bmp_path:
    root.destroy()
    raise SystemExit

try:
    with Image.open(bmp_path) as source:
        if source.format != 'BMP':
            raise ValueError('BMPファイルではありません')
        img = source.convert('RGB')
except Exception as e:
    messagebox.showerror('エラー', str(e))
    root.destroy()
    raise SystemExit

width, height = img.size
preview = img.copy()
preview.thumbnail((650, 380), Image.Resampling.LANCZOS)
pw, ph = preview.size
preview_photo = ImageTk.PhotoImage(preview, master=root)

x_position = tk.IntVar(master=root, value=(width - 1) // 2)
y_position = tk.IntVar(master=root, value=(height - 1) // 2)
output_dir = tk.StringVar(master=root, value=str(Path(bmp_path).parent))

root.title('BMP Grid Creator')
root.geometry('740x340')
root.minsize(650, 310)
root.deiconify()

tk.Label(root, text='BMP Grid Creator', font=('Arial', 16, 'bold')).pack(pady=(15, 5))
tk.Label(root, text=f'{Path(bmp_path).name}   |   {width} × {height} px').pack()

positions_label = tk.Label(root, font=('Arial', 11))
positions_label.pack(pady=(14, 5))

def refresh_positions():
    positions_label.config(text=f'縦ライン X = {x_position.get()} px   /   横ライン Y = {y_position.get()} px')

def choose_line(is_vertical):
    var = x_position if is_vertical else y_position
    maximum = (width if is_vertical else height) - 1
    axis = 'X' if is_vertical else 'Y'
    title = '① 縦ラインを選択（X座標）' if is_vertical else '② 横ラインを選択（Y座標）'
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()
    tk.Label(dialog, text=title, font=('Arial', 12, 'bold')).pack(pady=(12, 4))
    tk.Label(dialog, text='スライダーまたは画像のクリック／ドラッグで位置指定').pack()
    coordinate_label = tk.Label(dialog)
    coordinate_label.pack(pady=4)
    slider = tk.Scale(dialog, from_=0, to=max(0, maximum), orient='horizontal',
                      variable=var, length=650, resolution=1)
    slider.pack(padx=16)
    canvas = tk.Canvas(dialog, width=pw, height=ph, highlightthickness=0)
    canvas.pack(padx=16, pady=10)
    canvas.create_image(0, 0, anchor='nw', image=preview_photo)
    marker = canvas.create_line(0, 0, 0, 0, fill='red', width=2)

    def refresh(value=None):
        p = var.get()
        coordinate_label.config(text=f'{axis}座標：{p} / {maximum} px')
        if is_vertical:
            xx = p * (pw - 1) / max(1, width - 1)
            canvas.coords(marker, xx, 0, xx, ph)
        else:
            yy = p * (ph - 1) / max(1, height - 1)
            canvas.coords(marker, 0, yy, pw, yy)

    def pick(event):
        pixel = event.x if is_vertical else event.y
        preview_size = pw if is_vertical else ph
        p = round(pixel * maximum / max(1, preview_size - 1))
        var.set(max(0, min(maximum, p)))
        refresh()

    slider.config(command=refresh)
    canvas.bind('<Button-1>', pick)
    canvas.bind('<B1-Motion>', pick)
    tk.Button(dialog, text='この位置で決定', width=22, height=2,
              command=dialog.destroy).pack(pady=(0, 14))
    refresh()
    root.wait_window(dialog)
    refresh_positions()

selection_buttons = tk.Frame(root)
selection_buttons.pack(pady=5)
tk.Button(selection_buttons, text='縦ラインを選び直す', width=22,
          command=lambda: choose_line(True)).pack(side='left', padx=7)
tk.Button(selection_buttons, text='横ラインを選び直す', width=22,
          command=lambda: choose_line(False)).pack(side='left', padx=7)

folder_label = tk.Label(root, wraplength=680)
folder_label.pack(pady=(14, 4))

def refresh_folder():
    folder_label.config(text=f'保存先：{output_dir.get()}')

def choose_folder():
    folder = filedialog.askdirectory(title='Grid画像の保存先フォルダを選択',
                                    initialdir=output_dir.get())
    if folder:
        output_dir.set(folder)
        refresh_folder()

tk.Button(root, text='画像の保存先フォルダを選択', width=32,
          command=choose_folder).pack(pady=5)

def create_grid():
    output = Path(output_dir.get()) / f'{Path(bmp_path).stem}_grid.bmp'
    if output.exists() and not messagebox.askyesno('上書き確認', f'既に存在します。上書きしますか？\n{output}'):
        return
    try:
        x, y = x_position.get(), y_position.get()
        vertical_line = img.crop((x, 0, x + 1, height))
        horizontal_line = img.crop((0, y, width, y + 1))
        horizontal_stripes = vertical_line.resize((width, height), Image.Resampling.NEAREST)
        vertical_stripes = horizontal_line.resize((width, height), Image.Resampling.NEAREST)
        grid = ImageChops.difference(horizontal_stripes, vertical_stripes)
        grid.save(output, format='BMP')
        messagebox.showinfo('Grid完成', f'保存しました：\n{output}\n\nサイズ：{width} × {height} px')
    except Exception as e:
        messagebox.showerror('エラー', str(e))

tk.Button(root, text='Create Grid', font=('Arial', 12, 'bold'),
          width=25, height=2, command=create_grid).pack(pady=(10, 12))
refresh_positions()
refresh_folder()

def initial_selection():
    choose_line(True)
    choose_line(False)

root.after(150, initial_selection)
root.mainloop()
