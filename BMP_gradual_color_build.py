import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading
import random
import numpy as np
from PIL import Image
import cv2

class App:
    def __init__(self, root):
        self.root=root
        root.title('RGB Color Reconstruction')
        root.geometry('610x390')
        self.src=tk.StringVar(); self.dst=tk.StringVar()
        self.order=tk.StringVar(value='Random')
        self.duration=tk.StringVar(value='40'); self.hold=tk.StringVar(value='5')
        self.fps=tk.StringVar(value='30'); self.status=tk.StringVar(value='BMPを選択してください')
        frm=ttk.Frame(root,padding=15); frm.pack(fill='both',expand=True)
        ttk.Label(frm,text='BMP画像').grid(row=0,column=0,sticky='w')
        ttk.Entry(frm,textvariable=self.src,width=53).grid(row=0,column=1,sticky='ew',padx=5)
        ttk.Button(frm,text='選択',command=self.pick).grid(row=0,column=2)
        ttk.Label(frm,text='保存先 MP4').grid(row=1,column=0,sticky='w',pady=10)
        ttk.Entry(frm,textvariable=self.dst,width=53).grid(row=1,column=1,sticky='ew',padx=5)
        ttk.Button(frm,text='選択',command=self.save).grid(row=1,column=2)
        ttk.Label(frm,text='色の登場順').grid(row=2,column=0,sticky='w')
        ttk.Combobox(frm,textvariable=self.order,values=['Random','Rare first','Common first'],state='readonly',width=20).grid(row=2,column=1,sticky='w')
        for row,label,var in [(3,'復元時間（秒）',self.duration),(4,'完成後の静止（秒）',self.hold),(5,'FPS',self.fps)]:
            ttk.Label(frm,text=label).grid(row=row,column=0,sticky='w',pady=7)
            ttk.Entry(frm,textvariable=var,width=12).grid(row=row,column=1,sticky='w')
        self.progress=ttk.Progressbar(frm,maximum=100); self.progress.grid(row=6,column=0,columnspan=3,sticky='ew',pady=12)
        ttk.Label(frm,textvariable=self.status,wraplength=570).grid(row=7,column=0,columnspan=3,sticky='w')
        self.run_button=ttk.Button(frm,text='MP4を作成',command=self.start)
        self.run_button.grid(row=8,column=0,columnspan=3,pady=12)
        frm.columnconfigure(1,weight=1)
    def pick(self):
        p=filedialog.askopenfilename(filetypes=[('BMP image','*.bmp'),('All files','*.*')])
        if p:
            self.src.set(p)
            if not self.dst.get(): self.dst.set(str(Path(p).with_name(Path(p).stem+'_reconstruction.mp4')))
    def save(self):
        p=filedialog.asksaveasfilename(defaultextension='.mp4',filetypes=[('MP4 video','*.mp4')])
        if p: self.dst.set(p)
    def ui(self,percent,msg):
        self.root.after(0,lambda:(self.progress.configure(value=percent),self.status.set(msg)))
    def start(self):
        try:
            src=Path(self.src.get()); dst=Path(self.dst.get())
            if not src.is_file(): raise ValueError('BMPファイルを選択してください')
            if src.suffix.lower()!='.bmp': raise ValueError('BMPファイルを選択してください')
            if dst.suffix.lower()!='.mp4': raise ValueError('保存先は.mp4にしてください')
            if src.resolve()==dst.resolve(): raise ValueError('入力と出力は別ファイルにしてください')
            duration=float(self.duration.get()); hold=float(self.hold.get()); fps=int(self.fps.get())
            if duration<=0 or hold<0 or not 1<=fps<=60: raise ValueError('時間とFPSの値を確認してください')
            if duration*fps+hold*fps>200000: raise ValueError('動画が長すぎます')
            args=(src,dst,self.order.get(),duration,hold,fps)
        except Exception as e: messagebox.showerror('入力エラー',str(e)); return
        self.run_button.configure(state='disabled')
        threading.Thread(target=self.work,args=args,daemon=True).start()
    def work(self,src,dst,order,duration,hold,fps):
        writer=None
        try:
            self.ui(0,'BMPを解析しています...')
            rgb=np.asarray(Image.open(src).convert('RGB'),dtype=np.uint8)
            h,w,_=rgb.shape
            # Video dimensions must be even for reliable MP4 playback.
            outw=w+(w%2); outh=h+(h%2)
            pixels=rgb.reshape(-1,3)
            unique,inverse,counts=np.unique(pixels,axis=0,return_inverse=True,return_counts=True)
            n=len(unique)
            if order=='Rare first': indices=np.argsort(counts,kind='stable')
            elif order=='Common first': indices=np.argsort(-counts,kind='stable')
            else:
                indices=np.arange(n); np.random.default_rng().shuffle(indices)
            # Sort pixel offsets by their color ID, allowing each color's pixels to be filled once.
            positions=np.argsort(inverse,kind='stable')
            starts=np.zeros(n+1,dtype=np.int64)
            starts[1:]=np.cumsum(counts)
            flat=np.zeros((h*w,3),dtype=np.uint8)
            frames=max(1,round(duration*fps)); hold_frames=round(hold*fps)
            dst.parent.mkdir(parents=True,exist_ok=True)
            writer=cv2.VideoWriter(str(dst),cv2.VideoWriter_fourcc(*'mp4v'),fps,(outw,outh))
            if not writer.isOpened(): raise RuntimeError('MP4出力を開けません。保存先やOpenCVを確認してください')
            def emit():
                view=flat.reshape(h,w,3)
                bgr=cv2.cvtColor(view,cv2.COLOR_RGB2BGR)
                if outw!=w or outh!=h: bgr=cv2.copyMakeBorder(bgr,0,outh-h,0,outw-w,cv2.BORDER_CONSTANT,value=(0,0,0))
                writer.write(bgr)
            # First frame is entirely black. Frames thereafter cumulatively reveal color groups.
            emit()
            completed=0
            for frame in range(1,frames+1):
                target=(frame*n+frames-1)//frames
                target=min(n,target)
                while completed<target:
                    color_id=int(indices[completed])
                    offsets=positions[starts[color_id]:starts[color_id+1]]
                    flat[offsets]=unique[color_id]
                    completed+=1
                emit()
                if frame%max(1,fps//2)==0 or frame==frames:
                    self.ui(100*frame/frames,f'{completed:,} / {n:,} 色を表示 | {frame}/{frames} フレーム')
            for _ in range(hold_frames): emit()
            writer.release(); writer=None
            self.ui(100,f'完成！ {n:,}色 / {w}×{h} px → {dst}')
            self.root.after(0,lambda:messagebox.showinfo('完了',f'MP4を保存しました:\n{dst}\n異なる色: {n:,}種類'))
        except Exception as e:
            if writer is not None: writer.release()
            self.ui(0,f'エラー: {e}')
            self.root.after(0,lambda err=str(e):messagebox.showerror('エラー',err))
        finally:
            self.root.after(0,lambda:self.run_button.configure(state='normal'))

if __name__=='__main__':
    root=tk.Tk(); App(root); root.mainloop()
