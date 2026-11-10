"""BMP Cross Stripe Random Fade 008 — selectable blend modes."""
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
HOLD_SECONDS = 3
MAX_WIDTH = 1920


class App:
    def __init__(self, root):
        self.root = root
        root.title('BMP Cross Stripe Random Fade 008')
        root.geometry('700x430')
        self.status = tk.StringVar(value='BMP画像を選んでください')
        ttk.Label(root, text='各ピクセルが別々のタイミング・速度で徐々に変化 → 完成後3秒静止', font=('', 11)).pack(pady=(17, 6))
        ttk.Label(root, text='変換5秒 ＋ 完成画像の静止3秒（合計8秒）').pack(pady=3)
        ttk.Label(root, text='横・縦ストライプの合成方法を選択').pack(pady=3)
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
        dest = filedialog.asksaveasfilename(title='MP4の保存先', defaultextension='.mp4', initialfile=Path(src).stem + '_random_stripe_' + mode + '.mp4', filetypes=[('MP4動画', '*.mp4')])
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
            hold_frames = FPS * HOLD_SECONDS
            total_frames = frames + hold_frames
            writer = cv2.VideoWriter(dest, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (out_w, out_h))
            if not writer.isOpened():
                raise RuntimeError('MP4出力を開始できませんでした')
            # 最終的な横・縦ストライプ合成画像を先に作る
            base = hstripe
            over = vstripe
            if mode == 'difference':
                mixed = cv2.absdiff(base, over)
            elif mode == 'lighten':
                mixed = np.maximum(base, over)
            elif mode == 'darken':
                mixed = np.minimum(base, over)
            elif mode == 'screen':
                a16 = base.astype(np.uint16)
                b16 = over.astype(np.uint16)
                mixed = (255 - ((255 - a16) * (255 - b16) + 127) // 255).astype(np.uint8)
            else:
                raise ValueError('不明な合成モードです')
            target = mixed if opacity >= 1 else cv2.addWeighted(base, 1 - opacity, mixed, opacity, 0)

            # 各ピクセルごとに「開始時刻」と「変化にかかる時間」をランダム化。
            # どのピクセルも5秒以内に変換完了するよう設定する。
            rng = np.random.default_rng()
            start_at = rng.uniform(0.0, 0.72, (out_h, out_w)).astype(np.float32)
            fade_length = rng.uniform(0.05, 0.28, (out_h, out_w)).astype(np.float32)
            # 計算はfloat32。各画素のRGBが徐々に目標値へ近づく。
            original_f = original.astype(np.float32)
            delta = target.astype(np.float32) - original_f
            for i in range(frames):
                progress = i / (frames - 1) if frames > 1 else 1.0
                alpha = np.clip((progress - start_at) / fade_length, 0.0, 1.0)
                # 中間色を生成して各ピクセルを個別の速度で変換する
                frame = np.clip(original_f + delta * alpha[:, :, None], 0, 255).astype(np.uint8)
                writer.write(frame)
                if i % 5 == 0 or i == frames - 1:
                    self.update(round((i + 1) * 100 / total_frames),
                                f'ランダム変換中 {i + 1}/{frames} フレーム（{mode}）')
            # 変換終了後は完全な最終画像を3秒間保持
            for j in range(hold_frames):
                writer.write(target)
                if j % 10 == 0 or j == hold_frames - 1:
                    self.update(round((frames + j + 1) * 100 / total_frames),
                                f'完成画像を静止中 {j + 1}/{hold_frames} フレーム')
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
