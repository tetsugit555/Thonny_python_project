import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk, ImageChops

root = tk.Tk()
root.withdraw()
bmp_path = filedialog.askopenfilename(title='BMPファイルを選択', filetypes=[('BMP画像', '*.bmp')])
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

root.deiconify()
root.title('BMP RGB / Stripes / Grid')
root.geometry('760x950')
root.minsize(730, 750)

direction = tk.StringVar(value='horizontal')
position = tk.IntVar(value=(height - 1) // 2)
grid_x = tk.IntVar(value=(width - 1) // 2)
grid_y = tk.IntVar(value=(height - 1) // 2)
save_path = tk.StringVar()

tk.Label(root, text=f'画像サイズ：{width} × {height} px', font=('Arial', 12, 'bold')).pack(pady=(12, 4))
tk.Label(root, text=Path(bmp_path).name).pack()

frame = tk.LabelFrame(root, text='従来のRGB抽出 / Stripes の方向', padx=12, pady=7)
frame.pack(fill='x', padx=20, pady=10)
position_frame = tk.LabelFrame(root, text='従来の抽出位置', padx=12, pady=8)
position_frame.pack(fill='x', padx=20)
axis_label = tk.Label(position_frame)
axis_label.pack()

preview_frame = tk.LabelFrame(root, text='元画像プレビュー（クリック／ドラッグで位置指定）', padx=10, pady=10)
preview_frame.pack(padx=20, pady=10)
canvas = tk.Canvas(preview_frame, width=pw, height=ph, highlightthickness=0)
canvas.pack()
canvas.create_image(0, 0, anchor='nw', image=preview_photo)
line = canvas.create_line(0, 0, pw, 0, fill='red', width=2)

def update_preview(value=None):
    pos = position.get()
    if direction.get() == 'horizontal':
        axis_label.config(text=f'Y座標：{pos} px')
        y = pos * (ph - 1) / max(1, height - 1)
        canvas.coords(line, 0, y, pw, y)
    else:
        axis_label.config(text=f'X座標：{pos} px')
        x = pos * (pw - 1) / max(1, width - 1)
        canvas.coords(line, x, 0, x, ph)

def update_direction():
    maximum = (height if direction.get() == 'horizontal' else width) - 1
    scale.config(to=maximum)
    position.set(maximum // 2)
    update_preview()

for label, value in [('横方向（左 → 右）', 'horizontal'), ('縦方向（上 → 下）', 'vertical')]:
    tk.Radiobutton(frame, text=label, variable=direction, value=value, command=update_direction).pack(anchor='w')

scale = tk.Scale(position_frame, from_=0, to=max(0, height - 1), orient='horizontal', variable=position,
                 command=update_preview, resolution=1, length=650)
scale.pack()

def choose_position(event):
    if direction.get() == 'horizontal':
        pos = round(event.y * (height - 1) / max(1, ph - 1))
        pos = max(0, min(height - 1, pos))
    else:
        pos = round(event.x * (width - 1) / max(1, pw - 1))
        pos = max(0, min(width - 1, pos))
    position.set(pos)
    update_preview()

canvas.bind('<Button-1>', choose_position)
canvas.bind('<B1-Motion>', choose_position)
update_direction()

# グリッド用：縦ラインと横ラインを別々のダイアログで指定
def select_grid_line(axis):
    is_x = axis == 'x'
    var = grid_x if is_x else grid_y
    maximum = (width if is_x else height) - 1
    title = '① 縦ラインを選択（X座標）' if is_x else '② 横ラインを選択（Y座標）'
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()
    dialog.protocol('WM_DELETE_WINDOW', dialog.destroy)
    tk.Label(dialog, text=title, font=('Arial', 12, 'bold')).pack(pady=(12, 6))
    tk.Label(dialog, text='スライダーまたは画像のクリック／ドラッグで指定').pack()
    value_label = tk.Label(dialog)
    value_label.pack(pady=5)
    slider = tk.Scale(dialog, from_=0, to=max(0, maximum), orient='horizontal', length=650,
                      resolution=1, variable=var)
    slider.pack(padx=16)
    c = tk.Canvas(dialog, width=pw, height=ph, highlightthickness=0)
    c.pack(padx=16, pady=10)
    c.create_image(0, 0, anchor='nw', image=preview_photo)
    marker = c.create_line(0, 0, pw, ph, fill='red', width=2)

    def refresh(value=None):
        p = var.get()
        value_label.config(text=f'{"X" if is_x else "Y"}座標：{p} / {maximum} px')
        if is_x:
            xx = p * (pw - 1) / max(1, width - 1)
            c.coords(marker, xx, 0, xx, ph)
        else:
            yy = p * (ph - 1) / max(1, height - 1)
            c.coords(marker, 0, yy, pw, yy)

    def pick(event):
        p = round((event.x if is_x else event.y) * maximum / max(1, (pw if is_x else ph) - 1))
        var.set(max(0, min(maximum, p)))
        refresh()

    slider.config(command=refresh)
    c.bind('<Button-1>', pick)
    c.bind('<B1-Motion>', pick)
    tk.Button(dialog, text='この位置で決定', width=22, height=2, command=dialog.destroy).pack(pady=(0, 14))
    refresh()
    root.wait_window(dialog)
    update_grid_label()

def update_grid_label():
    grid_label.config(text=f'Grid用：縦 X={grid_x.get()} px ／ 横 Y={grid_y.get()} px')

grid_frame = tk.LabelFrame(root, text='Grid用の2本のライン', padx=12, pady=8)
grid_frame.pack(fill='x', padx=20, pady=(10, 4))
grid_label = tk.Label(grid_frame)
grid_label.pack()
grid_select_buttons = tk.Frame(grid_frame)
grid_select_buttons.pack(pady=5)
tk.Button(grid_select_buttons, text='① 縦ラインを選び直す', command=lambda: select_grid_line('x')).pack(side='left', padx=6)
tk.Button(grid_select_buttons, text='② 横ラインを選び直す', command=lambda: select_grid_line('y')).pack(side='left', padx=6)
update_grid_label()

def select_save():
    path = filedialog.asksaveasfilename(
        title='RGBテキストの保存先（Grid/BMPも同じフォルダに保存）',
        defaultextension='.txt', filetypes=[('テキストファイル', '*.txt')],
        initialfile=Path(bmp_path).stem + '_RGB.txt')
    if path:
        save_path.set(path)
        save_label.config(text=str(path), fg='black')

tk.Button(root, text='保存先フォルダを指定（TXTファイル名で指定）', command=select_save).pack(pady=(8, 5))
save_label = tk.Label(root, text='保存先未設定', fg='gray', wraplength=690)
save_label.pack()

def require_save():
    if not save_path.get():
        messagebox.showwarning('保存先未設定', '先に保存先を指定してください')
        return False
    return True

def confirm_overwrite(output):
    return not output.exists() or messagebox.askyesno('上書き確認', f'既に存在します。上書きしますか？\n{output}')

def extract_rgb():
    if not require_save():
        return
    pos = position.get()
    output = Path(save_path.get())
    if not confirm_overwrite(output):
        return
    try:
        with output.open('w', encoding='utf-8') as f:
            if direction.get() == 'horizontal':
                for x in range(width):
                    r, g, b = img.getpixel((x, pos))
                    f.write(f'{r:03d},{g:03d},{b:03d}\n')
                count = width
            else:
                for y in range(height):
                    r, g, b = img.getpixel((pos, y))
                    f.write(f'{r:03d},{g:03d},{b:03d}\n')
                count = height
        messagebox.showinfo('抽出完了', f'{count}ピクセル分のRGBデータを保存しました。\n{output}')
    except Exception as e:
        messagebox.showerror('エラー', str(e))

def create_stripes():
    if not require_save():
        return
    output = Path(save_path.get()).parent / (Path(bmp_path).stem + '_stripes.bmp')
    if not confirm_overwrite(output):
        return
    try:
        pos = position.get()
        if direction.get() == 'horizontal':
            strip = img.crop((0, pos, width, pos + 1))
        else:
            strip = img.crop((pos, 0, pos + 1, height))
        result = strip.resize((width, height), resample=Image.Resampling.NEAREST)
        result.save(output, format='BMP')
        messagebox.showinfo('Stripes 完成', f'保存しました：\n{output}\n\nサイズ：{width} × {height} px')
    except Exception as e:
        messagebox.showerror('エラー', str(e))

def create_grid():
    if not require_save():
        return
    output = Path(save_path.get()).parent / (Path(bmp_path).stem + '_grid.bmp')
    if not confirm_overwrite(output):
        return
    try:
        x, y = grid_x.get(), grid_y.get()
        vertical_line = img.crop((x, 0, x + 1, height))
        horizontal_line = img.crop((0, y, width, y + 1))
        horizontal_stripes = vertical_line.resize((width, height), Image.Resampling.NEAREST)
        vertical_stripes = horizontal_line.resize((width, height), Image.Resampling.NEAREST)
        # Photoshopの「差の絶対値」：RGB各成分の絶対差
        grid = ImageChops.difference(horizontal_stripes, vertical_stripes)
        grid.save(output, format='BMP')
        messagebox.showinfo('Grid 完成', f'保存しました：\n{output}\n\nサイズ：{width} × {height} px\n縦 X={x} ／ 横 Y={y}')
    except Exception as e:
        messagebox.showerror('エラー', str(e))

buttons = tk.Frame(root)
buttons.pack(pady=15)
tk.Button(buttons, text='GO - RGB抽出', font=('Arial', 10, 'bold'), width=18, height=2, command=extract_rgb).pack(side='left', padx=5)
tk.Button(buttons, text='Create Stripes', font=('Arial', 10, 'bold'), width=18, height=2, command=create_stripes).pack(side='left', padx=5)
tk.Button(buttons, text='Create Grid', font=('Arial', 10, 'bold'), width=18, height=2, command=create_grid).pack(side='left', padx=5)

# 最初に縦ライン、続けて横ラインを指定する
# afterでメインウィンドウの描画完了後にダイアログを表示する
def initial_grid_selection():
    select_grid_line('x')
    select_grid_line('y')
root.after(150, initial_grid_selection)
root.mainloop()
