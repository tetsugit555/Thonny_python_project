"""BMP画像の左端1ピクセル列を右へ伸ばすMP4動画生成ツール。"""
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import cv2
    import numpy as np
    from PIL import Image
except ImportError as exc:
    raise SystemExit(f"必要なライブラリがありません: {exc}\nThonnyで %pip install pillow numpy opencv-python")


def make_video(input_path, output_path, seconds, fps, max_width, progress):
    with Image.open(input_path) as img:
        rgb = np.asarray(img.convert('RGB'))
    h, w = rgb.shape[:2]
    # 元画像の縦横比を保持。大きな画像は動画用に縮小。
    scale = min(1.0, max_width / w)
    out_w = max(2, int(round(w * scale)) // 2 * 2)
    out_h = max(2, int(round(h * scale)) // 2 * 2)
    if (out_w, out_h) != (w, h):
        rgb = cv2.resize(rgb, (out_w, out_h), interpolation=cv2.INTER_AREA)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    # 画像の左端1列をそのまま右に複製した完成画像
    stripes = np.repeat(bgr[:, :1, :], out_w, axis=1)
    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (out_w, out_h))
    if not writer.isOpened():
        raise RuntimeError('MP4の書き込みを開始できません。保存先を確認してください。')
    total = max(2, round(seconds * fps))
    try:
        for frame_idx in range(total):
            # 最初は元画像、最後は100%ストライプ
            fraction = frame_idx / (total - 1)
            boundary = min(out_w, int(round(fraction * out_w)))
            frame = bgr.copy()
            if boundary:
                frame[:, :boundary, :] = stripes[:, :boundary, :]
            writer.write(frame)
            if frame_idx % max(1, fps // 2) == 0 or frame_idx == total - 1:
                progress(frame_idx + 1, total)
    finally:
        writer.release()


class App:
    def __init__(self, root):
        self.root = root
        root.title('BMP Stripe Wipe 001')
        root.geometry('580x320')
        root.resizable(False, False)
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.seconds = tk.StringVar(value='5')
        self.fps = tk.StringVar(value='30')
        self.width = tk.StringVar(value='1920')
        main = ttk.Frame(root, padding=16)
        main.pack(fill='both', expand=True)
        ttk.Label(main, text='BMP → 横ストライプ変換動画（左から右へ）', font=('', 12, 'bold')).pack(anchor='w', pady=(0, 12))
        for title, var, cmd in [
            ('入力BMP', self.input_file, self.pick_input),
            ('保存MP4', self.output_file, self.pick_output),
        ]:
            line = ttk.Frame(main)
            line.pack(fill='x', pady=4)
            ttk.Label(line, text=title, width=9).pack(side='left')
            ttk.Entry(line, textvariable=var).pack(side='left', fill='x', expand=True, padx=6)
            ttk.Button(line, text='参照...', command=cmd).pack(side='left')
        settings = ttk.Frame(main)
        settings.pack(fill='x', pady=14)
        for label, var, suffix in [('長さ', self.seconds, '秒'), ('FPS', self.fps, ''), ('最大幅', self.width, 'px')]:
            ttk.Label(settings, text=label).pack(side='left', padx=(0, 5))
            ttk.Entry(settings, textvariable=var, width=7).pack(side='left')
            ttk.Label(settings, text=suffix).pack(side='left', padx=(4, 18))
        ttk.Label(main, text='※ 縦横比を維持。元画像が大きい場合のみ縮小。音声なし。').pack(anchor='w')
        self.bar = ttk.Progressbar(main, maximum=100)
        self.bar.pack(fill='x', pady=(14, 5))
        self.status = ttk.Label(main, text='準備完了')
        self.status.pack(anchor='w')
        self.start_btn = ttk.Button(main, text='MP4動画を生成', command=self.start)
        self.start_btn.pack(pady=10)

    def pick_input(self):
        path = filedialog.askopenfilename(filetypes=[('BMP画像', '*.bmp'), ('画像', '*.bmp *.png *.jpg *.jpeg')])
        if path:
            self.input_file.set(path)
            if not self.output_file.get():
                self.output_file.set(os.path.splitext(path)[0] + '_stripe_wipe.mp4')

    def pick_output(self):
        path = filedialog.asksaveasfilename(defaultextension='.mp4', filetypes=[('MP4動画', '*.mp4')])
        if path:
            self.output_file.set(path)

    def start(self):
        try:
            src, dst = self.input_file.get(), self.output_file.get()
            if not os.path.isfile(src) or not dst:
                raise ValueError('入力BMPと保存先MP4を指定してください。')
            seconds, fps, width = float(self.seconds.get()), int(self.fps.get()), int(self.width.get())
            if not (0.1 <= seconds <= 3600 and 1 <= fps <= 120 and 2 <= width <= 16384):
                raise ValueError('長さ・FPS・最大幅の値を確認してください。')
            if os.path.abspath(src) == os.path.abspath(dst):
                raise ValueError('入力と出力は別のファイルにしてください。')
        except (ValueError, OSError) as exc:
            messagebox.showerror('設定エラー', str(exc))
            return
        self.start_btn.configure(state='disabled')
        self.bar['value'] = 0
        self.status.configure(text='生成中...')
        def update(done, total):
            self.root.after(0, lambda: self.show_progress(done, total))
        def work():
            try:
                make_video(src, dst, seconds, fps, width, update)
                self.root.after(0, lambda: self.finish(dst, None))
            except Exception as exc:
                self.root.after(0, lambda msg=str(exc): self.finish(dst, msg))
        threading.Thread(target=work, daemon=True).start()

    def show_progress(self, done, total):
        self.bar['value'] = done / total * 100
        self.status.configure(text=f'生成中... {done}/{total} フレーム ({done/total*100:.1f}%)')

    def finish(self, path, error):
        self.start_btn.configure(state='normal')
        if error:
            self.status.configure(text='エラー')
            messagebox.showerror('生成失敗', error)
        else:
            self.bar['value'] = 100
            self.status.configure(text='完成！')
            messagebox.showinfo('完成', f'MP4を保存しました。\n{path}')


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
