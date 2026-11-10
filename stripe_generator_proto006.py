"""BMP Cross Stripe Blend 006 — selectable blend modes."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading

try:
    import cv2
    import numpy as np
    from PIL import Image
except ImportError as exc:
    raise SystemExit(f'ライブラリ不足: {exc}\nThonnyで pillow, numpy, opencv-python をインストールしてください。')

FPS = 30
DURATION = 5
MAX_WIDTH = 1920


class App:
    def __init__(self, root):
        self.root = root
        root.title('BMP Cross Stripe Blend 006')
        root.geometry('650x390')
        self.status = tk.StringVar(value='BMP画像を選んでください')
        ttk.Label(root, text='横ストライプ：上→下 ／ 縦ストライプ：左→右', font=('', 11)).pack(pady=(17, 6))
        ttk.Label(root, text='縦ストライプの合成方法を選択').pack(pady=3)
        self.blend_mode = tk.StringVar(value='screen')
        modes = ttk.Frame(root)
        modes.pack(pady=5)
        for label, value in [('差の絶対値', 'difference'), ('スクリーン', 'screen'), ('比較（明）', 'lighten'), ('比較（暗）', 'darken')]:
            ttk.Radiobutton(modes, text=label, value=value, variable=self.blend_mode).pack(side='left', padx=7)
        controls = ttk.Frame(root)
        controls.pack(pady=8)
        ttk.Label(controls, text='縦ストライプの不透明度（%）').pack(side='left', padx=5)
        self.opacity = tk.IntVar(value=100)
        ttk.Spinbox(controls, from_=0, to=100, increment=10, width=5, textvariable=self.opacity).pack(side='left')
        self.btn = ttk.Button(root, text='BMPを選んでMP4を生成', command=self.choose)
        self.btn.pack(pady=6)
        self.bar = ttk.Progressbar(root, maximum=100, length=460)
        self.bar.pack(pady=10)
        ttk.Label(root, textvariable=self.status, wraplength=500).pack(pady=4)

    def choose(self):
        try:
            opacity = max(0, min(100, int(self.opacity.get()))) / 100.0
        except (ValueError, tk.TclError):
            messagebox.showerror('入力エラー', '不透明度は0〜100の整数にしてください')
            return
        mode = self.blend_mode.get()
        src = filedialog.askopenfilename(title='BMP画像を選択', filetypes=[('BMP画像', '*.bmp'), ('画像', '*.bmp *.png *.jpg *.jpeg')])
        if not src:
            return
        dest = filedialog.asksaveasfilename(title='MP4の保存先', defaultextension='.mp4', initialfile=Path(src).stem + '_cross_stripe_' + mode + '.mp4', filetypes=[('MP4動画', '*.mp4')])
        if not dest:
            return
        self.btn.configure(state='disabled')
        self.bar['value'] = 0
        threading.Thread(target=self.generate, args=(src, dest, opacity, mode), daemon=True).start()

    def update(self, percent, message):
        self.root.after(0, lambda: (self.bar.configure(value=percent), self.status.set(message)))

    def generate(self, src, dest, opacity, mode):
        writer = None
        try:
            with Image.open(src) as opened:
                img = opened.convert('RGB')
            w, h = img.size
            if w > MAX_WIDTH:
                new_w = MAX_WIDTH
                new_h = max(2, round(h * new_w / w))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            rgb = np.asarray(img, dtype=np.uint8)
            h, w = rgb.shape[:2]
            out_w = w - w % 2
            out_h = h - h % 2
            if out_w < 2 or out_h < 2:
                raise ValueError('画像が小さすぎます（縦横2px以上必要）')
            # 左端の縦1列を横方向へ複製（横ストライプ）
            horizontal = np.repeat(rgb[:, :1, :], w, axis=1)
            # 上端の横1行を縦方向へ複製（縦ストライプ）
            vertical = np.repeat(rgb[:1, :, :], h, axis=0)
            original = cv2.cvtColor(rgb[:out_h, :out_w], cv2.COLOR_RGB2BGR)
            hstripe = cv2.cvtColor(horizontal[:out_h, :out_w], cv2.COLOR_RGB2BGR)
            vstripe = cv2.cvtColor(vertical[:out_h, :out_w], cv2.COLOR_RGB2BGR)
            frames = FPS * DURATION
            writer = cv2.VideoWriter(dest, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (out_w, out_h))
            if not writer.isOpened():
                raise RuntimeError('MP4出力を開始できませんでした')
            for i in range(frames):
                progress = i / (frames - 1)
                y = min(out_h, round(out_h * progress))
                x = min(out_w, round(out_w * progress))
                frame = original.copy()
                # 第1層：上から横ストライプに置換
                if y:
                    frame[:y, :, :] = hstripe[:y, :, :]
                # 第2層：左から縦ストライプを選択した方式で合成
                if x and opacity > 0:
                    base = frame[:, :x, :]
                    over = vstripe[:, :x, :]
                    if mode == 'difference':
                        # 差の絶対値：RGBチャンネルごとに |下 - 上|
                        mixed = cv2.absdiff(base, over)
                    elif mode == 'lighten':
                        # 比較（明）：RGB各チャンネルで明るい方を採用
                        mixed = np.maximum(base, over)
                    elif mode == 'darken':
                        # 比較（暗）：RGB各チャンネルで暗い方を採用
                        mixed = np.minimum(base, over)
                    elif mode == 'screen':
                        # スクリーン：255 - (255-A)*(255-B)/255
                        a16 = base.astype(np.uint16)
                        b16 = over.astype(np.uint16)
                        mixed = (255 - ((255 - a16) * (255 - b16) + 127) // 255).astype(np.uint8)
                    else:
                        raise ValueError('不明な合成モードです')
                    if opacity >= 1:
                        frame[:, :x, :] = mixed
                    else:
                        frame[:, :x, :] = cv2.addWeighted(base, 1 - opacity, mixed, opacity, 0)
                writer.write(frame)
                if i % 5 == 0 or i == frames - 1:
                    self.update(round((i + 1) * 100 / frames), f'生成中 {i + 1}/{frames} フレーム（{mode}）')
            writer.release()
            writer = None
            self.update(100, f'完成: {dest}')
            self.root.after(0, lambda: messagebox.showinfo('完成', f'MP4を保存しました。\n{dest}'))
        except Exception as exc:
            msg = str(exc)
            self.update(0, '生成に失敗しました')
            self.root.after(0, lambda: messagebox.showerror('エラー', msg))
        finally:
            if writer is not None:
                writer.release()
            self.root.after(0, lambda: self.btn.configure(state='normal'))


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
