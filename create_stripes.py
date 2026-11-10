import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk

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
root.deiconify()
root.title('BMP RGB 抽出 & Stripes')
root.geometry('740x940')
root.minsize(710, 650)

direction = tk.StringVar(value='horizontal')
position = tk.IntVar(value=(height - 1)//2)
save_path = tk.StringVar()

tk.Label(root, text=f'画像サイズ：{width} × {height} px', font=('Arial', 12, 'bold')).pack(pady=(12, 4))
tk.Label(root, text=Path(bmp_path).name).pack()
frame = tk.LabelFrame(root, text='抽出方向', padx=12, pady=7)
frame.pack(fill='x', padx=20, pady=10)

position_frame = tk.LabelFrame(root, text='抽出位置', padx=12, pady=8)
position_frame.pack(fill='x', padx=20)
axis_label = tk.Label(position_frame)
axis_label.pack()

preview_frame = tk.LabelFrame(root, text='元画像プレビュー（クリック／ドラッグで位置指定）', padx=10, pady=10)
preview_frame.pack(padx=20, pady=10)
canvas = tk.Canvas(preview_frame, width=pw, height=ph, highlightthickness=0)
canvas.pack()
preview_photo = ImageTk.PhotoImage(preview)
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

scale = tk.Scale(position_frame, from_=0, to=max(0, height-1), orient='horizontal', variable=position, command=update_preview, resolution=1, length=650)
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

def select_save():
    path = filedialog.asksaveasfilename(title='RGBテキストの保存先', defaultextension='.txt', filetypes=[('テキストファイル', '*.txt')], initialfile=Path(bmp_path).stem + '_RGB.txt')
    if path:
        save_path.set(path)
        save_label.config(text=str(path), fg='black')

tk.Button(root, text='TXT保存先を選択', command=select_save).pack(pady=(10, 5))
save_label = tk.Label(root, text='保存先未設定', fg='gray', wraplength=650)
save_label.pack()

def require_save():
    if not save_path.get():
        messagebox.showwarning('保存先未設定', '先にTXT保存先を選択してください')
        return False
    return True

def extract_rgb():
    if not require_save():
        return
    pos = position.get()
    try:
        with open(save_path.get(), 'w', encoding='utf-8') as f:
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
        messagebox.showinfo('抽出完了', f'{count}ピクセル分のRGBデータを保存しました。')
    except Exception as e:
        messagebox.showerror('エラー', str(e))

def create_stripes():
    if not require_save():
        return
    pos = position.get()
    output = Path(save_path.get()).parent / (Path(bmp_path).stem + '_stripes.bmp')
    if output.exists():
        if not messagebox.askyesno('上書き確認', f'既に存在します。上書きしますか？\n{output}'):
            return
    try:
        if direction.get() == 'horizontal':
            # 横1行を縦方向に複製 → 縦ストライプ
            strip = img.crop((0, pos, width, pos + 1))
        else:
            # 縦1列を横方向に複製 → 横ストライプ
            strip = img.crop((pos, 0, pos + 1, height))
        result = strip.resize((width, height), resample=Image.Resampling.NEAREST)
        result.save(output, format='BMP')
        messagebox.showinfo('Stripes 完成', f'保存しました：\n{output}\n\nサイズ：{width} × {height} px')
    except Exception as e:
        messagebox.showerror('エラー', str(e))

buttons = tk.Frame(root)
buttons.pack(pady=18)
tk.Button(buttons, text='GO - RGB抽出', font=('Arial', 11, 'bold'), width=19, height=2, command=extract_rgb).pack(side='left', padx=8)
tk.Button(buttons, text='Create Stripes', font=('Arial', 11, 'bold'), width=19, height=2, command=create_stripes).pack(side='left', padx=8)
root.mainloop()
