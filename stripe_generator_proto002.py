"""BMP Stripe Wipe 002: horizontal stripes reveal from top to bottom."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading

try:
    import cv2
    import numpy as np
    from PIL import Image
except ImportError as exc:
    raise SystemExit(f"必要なライブラリがありません: {exc}\nThonnyのパッケージ管理で pillow, numpy, opencv-python をインストールしてください。")

FPS = 30
DURATION = 5
MAX_WIDTH = 1920

class App:
    def __init__(self, root):
        self.root = root
        root.title('BMP Stripe Wipe 002 — 上から横ストライプ化')
        root.geometry('520x240')
        self.status = tk.StringVar(value='BMPを選択してください')
        ttk.Label(root, text='左端1列のRGB → 横ストライプを上から下へ展開', font=('', 11)).pack(pady=(18, 10))
        self.btn = ttk.Button(root, text='BMPを選んでMP4を生成', command=self.choose)
        self.btn.pack(pady=8)
        self.bar = ttk.Progressbar(root, maximum=100, length=440)
        self.bar.pack(pady=12)
        ttk.Label(root, textvariable=self.status, wraplength=480).pack(pady=4)

    def choose(self):
        src = filedialog.askopenfilename(title='BMP画像を選択', filetypes=[('BMP画像', '*.bmp'), ('画像', '*.bmp *.png *.jpg *.jpeg')])
        if not src:
            return
        dest = filedialog.asksaveasfilename(title='MP4の保存先', defaultextension='.mp4', initialfile=Path(src).stem+'_stripe_top_down.mp4', filetypes=[('MP4動画', '*.mp4')])
        if not dest:
            return
        self.btn.config(state='disabled')
        self.bar['value'] = 0
        threading.Thread(target=self.generate, args=(src, dest), daemon=True).start()

    def update(self, percent, message):
        self.root.after(0, lambda: (self.bar.configure(value=percent), self.status.set(message)))

    def generate(self, src, dest):
        writer = None
        try:
            img = Image.open(src).convert('RGB')
            w, h = img.size
            if w > MAX_WIDTH:
                new_w = MAX_WIDTH
                new_h = max(1, round(h * new_w / w))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            rgb = np.array(img, dtype=np.uint8)
            h, w = rgb.shape[:2]
            # 左端1列の各RGB値を横方向へコピー（平均化しない）
            stripe = np.repeat(rgb[:, :1, :], w, axis=1)
            original_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            stripe_bgr = cv2.cvtColor(stripe, cv2.COLOR_RGB2BGR)
            # 動画コーデックの互換性のため偶数サイズにする
            out_w = w - w % 2
            out_h = h - h % 2
            if out_w < 2 or out_h < 2:
                raise ValueError('画像のサイズが小さすぎます')
            writer = cv2.VideoWriter(dest, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (out_w, out_h))
            if not writer.isOpened():
                raise RuntimeError('MP4ファイルを開けませんでした')
            frames = FPS * DURATION
            for i in range(frames):
                # 0%から100%まで進行。最終フレームは完全なストライプ。
                boundary = round(h * i / (frames - 1))
                frame = original_bgr.copy()
                frame[:boundary, :, :] = stripe_bgr[:boundary, :, :]
                writer.write(frame[:out_h, :out_w])
                if i % 5 == 0 or i == frames - 1:
                    self.update(round((i+1)*100/frames), f'生成中… {i+1}/{frames} フレーム')
            writer.release()
            writer = None
            self.root.after(0, lambda: messagebox.showinfo('完了', f'MP4を保存しました。\n{dest}'))
            self.update(100, f'完了: {dest}')
        except Exception as exc:
            msg = str(exc)
            self.root.after(0, lambda: messagebox.showerror('エラー', msg))
            self.update(0, '生成に失敗しました')
        finally:
            if writer is not None:
                writer.release()
            self.root.after(0, lambda: self.btn.config(state='normal'))

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
