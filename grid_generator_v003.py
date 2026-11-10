"""BMP Cross Stripe + RGB Data Stream 015 (5s original + 5s transform + 3s hold + 40s text)."""
import os
import random
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:
    raise SystemExit(f'ライブラリ不足: {exc}\nThonnyで pillow, numpy, opencv-python をインストールしてください。')

FPS = 30
ORIGINAL_SEC = 5
TRANSFORM_SEC = 5
HOLD_SEC = 3
STREAM_SEC = 40
MAX_WIDTH = 1920
CHUNK_CHARS = 110


def find_font(size):
    for path in [r'C:\Windows\Fonts\consola.ttf', r'C:\Windows\Fonts\lucon.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf']:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rgb_text_chunks(rgb):
    """Generate RGB text directly from the pixels; never write a TXT file.

    Each pixel is represented as R,G,B, in left-to-right/top-to-bottom order.
    The generator only keeps one row of strings in memory at a time.
    """
    for row in rgb:
        line = ' '.join(f'{int(r)},{int(g)},{int(b)}' for r, g, b in row)
        while len(line) > CHUNK_CHARS:
            cut = line.rfind(' ', 1, CHUNK_CHARS + 1)
            if cut < CHUNK_CHARS // 3:
                cut = CHUNK_CHARS
            yield line[:cut]
            line = line[cut:].lstrip()
        if line:
            yield line


def screen_mix(a, b):
    x = a.astype(np.uint16)
    y = b.astype(np.uint16)
    return (255 - ((255 - x) * (255 - y) + 127) // 255).astype(np.uint8)


def blend_stripes(base, over, mode):
    if mode == 'difference':
        return cv2.absdiff(base, over)
    if mode == 'screen':
        return screen_mix(base, over)
    if mode == 'lighten':
        return np.maximum(base, over)
    if mode == 'darken':
        return np.minimum(base, over)
    raise ValueError('不明な合成モード')


class App:
    def __init__(self, root):
        self.root = root
        root.title('BMP Cross Stripe + RGB Stream 015')
        root.geometry('760x570')
        self.bmp = tk.StringVar()
        self.output = tk.StringVar()
        self.mode = tk.StringVar(value='screen')
        self.video_format = tk.StringVar(value='standard')
        self.opacity = tk.IntVar(value=100)
        self.photo_opacity = tk.IntVar(value=25)
        self.status = tk.StringVar(value='JPEGをBMPに変換するか、画像を選択してください。RGBテキストは内部で自動生成します。')
        panel = ttk.Frame(root, padding=16)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='BMP CROSS STRIPE + RGB DATA STREAM 015', font=('', 14, 'bold')).pack(anchor='w', pady=(0, 7))
        ttk.Label(panel, text='元画像5秒 → ランダム変換5秒 → 完成静止3秒 → RGB文字40秒（合計53秒）').pack(anchor='w', pady=(0, 9))
        ttk.Label(panel, text='RGB文字は画像から自動生成（TXT保存なし）').pack(anchor='w', pady=(0, 7))
        convert_row = ttk.Frame(panel)
        convert_row.pack(fill='x', pady=(3, 8))
        ttk.Button(convert_row, text='JPEG → BMP変換...', command=self.convert_jpeg).pack(side='left')
        ttk.Label(convert_row, text='24bit BMPとして保存し、下の入力欄に自動設定').pack(side='left', padx=12)
        self.path_row(panel, 'BMP画像', self.bmp, self.pick_bmp)
        self.path_row(panel, '保存MP4', self.output, self.pick_output)
        ttk.Label(panel, text='ストライプ合成モード').pack(anchor='w', pady=(12, 3))
        modes = ttk.Frame(panel)
        modes.pack(anchor='w')
        for label, value in [('差の絶対値', 'difference'), ('スクリーン', 'screen'), ('比較（明）', 'lighten'), ('比較（暗）', 'darken')]:
            ttk.Radiobutton(modes, text=label, value=value, variable=self.mode).pack(side='left', padx=(0, 14))
        ttk.Label(panel, text='動画出力形式').pack(anchor='w', pady=(12, 3))
        formats = ttk.Frame(panel)
        formats.pack(anchor='w')
        ttk.Radiobutton(formats, text='通常版（元画像の比率）', value='standard', variable=self.video_format).pack(side='left', padx=(0, 22))
        ttk.Radiobutton(formats, text='Instagramリール（1080×1920）', value='reels', variable=self.video_format).pack(side='left')
        settings = ttk.Frame(panel)
        settings.pack(anchor='w', pady=14)
        ttk.Label(settings, text='縦ストライプ不透明度 %').pack(side='left')
        ttk.Spinbox(settings, from_=0, to=100, width=5, textvariable=self.opacity).pack(side='left', padx=(6, 25))
        ttk.Label(settings, text='後半の元写真の濃さ %').pack(side='left')
        ttk.Spinbox(settings, from_=0, to=100, width=5, textvariable=self.photo_opacity).pack(side='left', padx=6)
        self.button = ttk.Button(panel, text='53秒のMP4を生成', command=self.start)
        self.button.pack(fill='x', pady=(4, 10))
        self.bar = ttk.Progressbar(panel, maximum=100)
        self.bar.pack(fill='x')
        ttk.Label(panel, textvariable=self.status, wraplength=680).pack(anchor='w', pady=10)

    def path_row(self, parent, title, var, command):
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text=title, width=11).pack(side='left')
        ttk.Entry(row, textvariable=var).pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='参照...', command=command).pack(side='left', padx=(6, 0))

    def convert_jpeg(self):
        source = filedialog.askopenfilename(
            title='変換するJPEG画像を選択',
            filetypes=[('JPEG画像', '*.jpg *.jpeg'), ('すべてのファイル', '*.*')])
        if not source:
            return
        destination = filedialog.asksaveasfilename(
            title='変換後のBMP保存先',
            initialdir=str(Path(source).parent),
            initialfile=Path(source).stem + '.bmp',
            defaultextension='.bmp',
            filetypes=[('BMP画像', '*.bmp')])
        if not destination:
            return
        if os.path.abspath(source) == os.path.abspath(destination):
            messagebox.showerror('変換エラー', '元画像とは別のファイル名を指定してください。')
            return
        if os.path.exists(destination) and not messagebox.askyesno('上書き確認', '既存のBMPを上書きしますか？'):
            return
        try:
            with Image.open(source) as opened:
                # 24bit RGB BMP (8 bits per channel, no alpha)
                rgb_image = opened.convert('RGB')
                rgb_image.save(destination, format='BMP')
            self.bmp.set(destination)
            self.output.set(str(Path(destination).with_name(Path(destination).stem + '_cross_rgb_015.mp4')))
            self.status.set(f'BMP変換完了：{destination}')
            messagebox.showinfo('BMP変換完了', f'24bit BMPを保存しました。\n{destination}')
        except Exception as exc:
            messagebox.showerror('BMP変換エラー', str(exc))

    def pick_bmp(self):
        path = filedialog.askopenfilename(title='BMP画像を選択', filetypes=[('BMP', '*.bmp'), ('画像', '*.bmp *.png *.jpg *.jpeg')])
        if path:
            self.bmp.set(path)
            if not self.output.get():
                self.output.set(str(Path(path).with_name(Path(path).stem + '_cross_rgb_015.mp4')))

    def pick_output(self):
        path = filedialog.asksaveasfilename(title='MP4保存先', defaultextension='.mp4', filetypes=[('MP4', '*.mp4')])
        if path:
            self.output.set(path)

    def update(self, n, msg):
        self.root.after(0, lambda: (self.bar.configure(value=n), self.status.set(msg)))

    def start(self):
        bmp, out = self.bmp.get(), self.output.get()
        if not os.path.isfile(bmp) or not out:
            messagebox.showerror('入力エラー', '画像とMP4保存先を指定してください。')
            return
        try:
            opacity = int(self.opacity.get())
            photo = int(self.photo_opacity.get())
            if not (0 <= opacity <= 100 and 0 <= photo <= 100):
                raise ValueError()
        except (ValueError, tk.TclError):
            messagebox.showerror('入力エラー', '不透明度は0〜100の整数で指定してください。')
            return
        if os.path.abspath(out) == os.path.abspath(bmp):
            messagebox.showerror('入力エラー', '出力ファイルは入力と別にしてください。')
            return
        if os.path.exists(out) and not messagebox.askyesno('上書き確認', '既存のMP4を上書きしますか？'):
            return
        self.button.configure(state='disabled')
        self.bar['value'] = 0
        threading.Thread(target=self.generate, args=(bmp, out, self.mode.get(), opacity / 100, photo / 100, self.video_format.get()), daemon=True).start()

    def generate(self, bmp, out, mode, opacity, photo_opacity, video_format):
        writer = None
        try:
            with Image.open(bmp) as opened:
                img = opened.convert('RGB')
            w, h = img.size
            if w > MAX_WIDTH:
                img = img.resize((MAX_WIDTH, max(2, round(h * MAX_WIDTH / w))), Image.Resampling.LANCZOS)
            rgb = np.asarray(img, dtype=np.uint8)
            h, w = rgb.shape[:2]
            w, h = w - w % 2, h - h % 2
            if w < 2 or h < 2:
                raise ValueError('画像は縦横2px以上必要です')
            rgb = rgb[:h, :w].copy()
            original = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            horizontal = np.repeat(original[:, :1, :], w, axis=1)
            vertical = np.repeat(original[:1, :, :], h, axis=0)
            mixed = blend_stripes(horizontal, vertical, mode)
            target = mixed if opacity == 1 else cv2.addWeighted(horizontal, 1 - opacity, mixed, opacity, 0)
            if video_format == 'reels':
                out_w, out_h = 1080, 1920
                scale = min(out_w / w, out_h / h)
                display_w = max(2, int(w * scale) // 2 * 2)
                display_h = max(2, int(h * scale) // 2 * 2)
                left = (out_w - display_w) // 2
                top = (out_h - display_h) // 2
                def format_frame(frame):
                    canvas = np.zeros((out_h, out_w, 3), dtype=np.uint8)
                    resized = cv2.resize(frame, (display_w, display_h), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
                    canvas[top:top+display_h, left:left+display_w] = resized
                    return canvas
            else:
                out_w, out_h = w, h
                def format_frame(frame):
                    return frame
            total = FPS * (ORIGINAL_SEC + TRANSFORM_SEC + HOLD_SEC + STREAM_SEC)
            writer = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (out_w, out_h))
            if not writer.isOpened():
                raise RuntimeError('MP4を作成できませんでした。保存先を確認してください。')
            rng = np.random.default_rng()
            starts = rng.uniform(0.0, 0.72, (h, w)).astype(np.float32)
            fades = rng.uniform(0.05, 0.28, (h, w)).astype(np.float32)
            original_f = original.astype(np.float32)
            delta = target.astype(np.float32) - original_f
            count = 0
            for i in range(FPS * ORIGINAL_SEC):
                writer.write(format_frame(original))
                count += 1
                if i % 15 == 0:
                    self.update(count * 100 / total, '第1部：元画像を5秒表示中...')
            for i in range(FPS * TRANSFORM_SEC):
                progress = i / (FPS * TRANSFORM_SEC - 1)
                alpha = np.clip((progress - starts) / fades, 0, 1)
                frame = np.clip(original_f + delta * alpha[:, :, None], 0, 255).astype(np.uint8)
                writer.write(format_frame(frame))
                count += 1
                if i % 10 == 0:
                    self.update(count * 100 / total, '第2部：ピクセルをランダム変換中...')
            for i in range(FPS * HOLD_SEC):
                writer.write(format_frame(target))
                count += 1
                if i % 15 == 0:
                    self.update(count * 100 / total, '第3部：完成したストライプを3秒静止中...')
            # Final section: fade original photo over stripes, then scroll RGB pixel values in white.
            # Keep text separate from the photo blend, so white glyphs remain crisp.
            font_size = max(12, round(23 * w / 1920))
            font = find_font(font_size)
            randomizer = random.Random()
            chunks = iter(rgb_text_chunks(rgb))
            active = []
            next_spawn = 0.0
            # Read sequentially; restart at the first pixel if the image is small.
            empty = False
            for i in range(FPS * STREAM_SEC):
                t = i / FPS
                # Photo opacity ramps up over the first 2 seconds of this section.
                photo_alpha = photo_opacity * min(1.0, t / 2.0)
                base = cv2.addWeighted(target, 1 - photo_alpha, original, photo_alpha, 0)
                while t >= next_spawn and len(active) < 65 and not empty:
                    try:
                        content = next(chunks)
                    except StopIteration:
                        chunks = iter(rgb_text_chunks(rgb))
                        try:
                            content = next(chunks)
                        except StopIteration:
                            empty = True
                            break
                    y = randomizer.randint(0, max(0, h - font_size - 4))
                    speed = randomizer.uniform(110, 420) * w / 1920
                    gray = randomizer.randint(175, 255)
                    active.append([float(w + randomizer.randint(0, 100)), y, speed, content, gray])
                    next_spawn += randomizer.uniform(0.07, 0.25)
                canvas = Image.fromarray(cv2.cvtColor(base, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(canvas)
                keep = []
                for item in active:
                    x, y, speed, content, gray = item
                    draw.text((int(x), y), content, font=font, fill=(gray, gray, gray))
                    item[0] = x - speed / FPS
                    if item[0] + draw.textlength(content, font=font) > 0:
                        keep.append(item)
                active = keep
                writer.write(format_frame(cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR)))
                count += 1
                if i % 10 == 0:
                    self.update(count * 100 / total, '第4部：元写真を薄く重ねてRGBデータを流しています...')
            writer.release()
            writer = None
            self.update(100, f'完成：{out}')
            self.root.after(0, lambda: messagebox.showinfo('完成', f'53秒のMP4を保存しました。\n{out}'))
        except Exception as exc:
            error = str(exc)
            self.update(0, '生成に失敗しました')
            self.root.after(0, lambda: messagebox.showerror('エラー', error))
        finally:
            if writer is not None:
                writer.release()
            self.root.after(0, lambda: self.button.configure(state='normal'))


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
