import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import json
import threading
import sys
import platform

# --- 配置区域 ---
# 如果你安装了 ttkbootstrap，这里会启用美化皮肤
# 如果没有安装，会自动降级为原生丑一点的界面，但功能完全一样
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    STYLE_THEME = "cosmo" # 可选: cosmo, flatly, journal, minty
except ImportError:
    import tkinter.ttk as ttk
    STYLE_THEME = None

class VideoClipperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BatchClipFlow - 批量视频分段工具 (便携版)")
        self.root.geometry("950x750")
        
        # 1. 自动检测 FFmpeg
        self.ffmpeg_path = self.find_ffmpeg()
        
        # 2. 数据变量
        self.video_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.clip_list = [] 
        
        # 3. 构建界面
        self.setup_ui()
        
        # 4. 启动检查
        self.check_environment()

    def find_ffmpeg(self):
        """
        查找逻辑：
        1. 优先找当前脚本所在目录下的 ffmpeg.exe (便携模式)
        2. 其次找系统环境变量里的 ffmpeg
        """
        # 获取当前文件所在目录
        if getattr(sys, 'frozen', False):
            # 如果是被打包成exe的情况
            base_path = os.path.dirname(sys.executable)
        else:
            # 正常运行py脚本的情况
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        # 检查当前目录
        local_ffmpeg = os.path.join(base_path, "ffmpeg.exe")
        if platform.system() != "Windows":
             local_ffmpeg = os.path.join(base_path, "ffmpeg") # Mac/Linux不带exe后缀

        if os.path.exists(local_ffmpeg):
            return local_ffmpeg
        
        # 检查系统PATH
        from shutil import which
        system_ffmpeg = which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg
            
        return None

    def check_environment(self):
        if self.ffmpeg_path:
            # 找到了，显示路径信息
            source = "本地文件" if os.path.dirname(self.ffmpeg_path) in [os.getcwd(), os.path.dirname(os.path.abspath(__file__))] else "系统环境"
            self.status_label.config(text=f"就绪 | FFmpeg来源: {source} ({self.ffmpeg_path})", foreground="green")
        else:
            # 没找到，弹窗警告
            self.status_label.config(text="错误: 未找到 ffmpeg.exe", foreground="red")
            self.root.after(1000, lambda: messagebox.showwarning(
                "缺少组件", 
                "无法剪辑！未找到 ffmpeg.exe。\n\n解决方法：\n请下载 ffmpeg.exe 并将其放入本软件的同一文件夹内。"
            ))

    def setup_ui(self):
        # === 顶部：文件选择 ===
        top_frame = ttk.Labelframe(self.root, text="输入输出设置", padding=15)
        top_frame.pack(fill=tk.X, padx=15, pady=10)

        # 源视频
        ttk.Label(top_frame, text="源视频:").grid(row=0, column=0, sticky="e", padx=5)
        ttk.Entry(top_frame, textvariable=self.video_path, width=70).grid(row=0, column=1, padx=5)
        ttk.Button(top_frame, text="📂 选择视频", command=self.select_video).grid(row=0, column=2)

        # 输出路径
        ttk.Label(top_frame, text="保存到:").grid(row=1, column=0, sticky="e", padx=5, pady=10)
        ttk.Entry(top_frame, textvariable=self.output_dir, width=70).grid(row=1, column=1, padx=5, pady=10)
        ttk.Button(top_frame, text="📂 选择文件夹", command=self.select_output).grid(row=1, column=2)

        # === 中部：列表 ===
        list_frame = ttk.Frame(self.root, padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        cols = ("ID", "Start", "End", "Name", "Status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        
        self.tree.heading("ID", text="序号")
        self.tree.heading("Start", text="开始时间")
        self.tree.heading("End", text="结束时间")
        self.tree.heading("Name", text="输出文件名")
        self.tree.heading("Status", text="状态")

        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Start", width=120, anchor="center")
        self.tree.column("End", width=120, anchor="center")
        self.tree.column("Name", width=350, anchor="w")
        self.tree.column("Status", width=100, anchor="center")

        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # === 底部：操作区 ===
        control_frame = ttk.Labelframe(self.root, text="剪辑操作", padding=15)
        control_frame.pack(fill=tk.X, padx=15, pady=10)

        # 输入行
        input_frame = ttk.Frame(control_frame)
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="开始(HH:MM:SS):").pack(side=tk.LEFT)
        self.entry_start = ttk.Entry(input_frame, width=12)
        self.entry_start.pack(side=tk.LEFT, padx=5)
        self.entry_start.insert(0, "00:00:00")

        ttk.Label(input_frame, text="结束:").pack(side=tk.LEFT, padx=(15, 0))
        self.entry_end = ttk.Entry(input_frame, width=12)
        self.entry_end.pack(side=tk.LEFT, padx=5)
        self.entry_end.insert(0, "00:00:10")

        ttk.Label(input_frame, text="文件名:").pack(side=tk.LEFT, padx=(15, 0))
        self.entry_name = ttk.Entry(input_frame, width=20)
        self.entry_name.pack(side=tk.LEFT, padx=5)
        
        # 按钮行
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=15)

        ttk.Button(btn_frame, text="⬇ 添加片段", command=self.add_clip).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ 删除选中", command=self.delete_clip).pack(side=tk.LEFT, padx=5)
        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Button(btn_frame, text="💾 保存清单", command=self.save_project).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 读取清单", command=self.load_project).pack(side=tk.LEFT, padx=5)

        self.run_btn = ttk.Button(btn_frame, text="🚀 开始批量剪辑", command=self.start_processing_thread, bootstyle="success" if STYLE_THEME else None)
        self.run_btn.pack(side=tk.RIGHT, padx=10)

        # 进度和状态
        self.progress = ttk.Progressbar(self.root, mode='determinate')
        self.progress.pack(fill=tk.X, padx=15, pady=(0, 5))
        
        self.status_label = ttk.Label(self.root, text="正在初始化...", font=("Arial", 9))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=5)

    # --- 逻辑功能 ---
    def select_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi *.flv *.ts")])
        if path:
            self.video_path.set(path)
            if not self.output_dir.get():
                self.output_dir.set(os.path.dirname(path))

    def select_output(self):
        path = filedialog.askdirectory()
        if path: self.output_dir.set(path)

    def add_clip(self):
        s, e, n = self.entry_start.get(), self.entry_end.get(), self.entry_name.get()
        if not n: n = f"clip_{len(self.clip_list)+1}"
        
        self.clip_list.append({"start": s, "end": e, "name": n, "status": "等待"})
        self.refresh_tree()
        
        # 智能流：把结束时间自动填入下一次的开始时间
        self.entry_start.delete(0, tk.END)
        self.entry_start.insert(0, e)
        self.entry_name.delete(0, tk.END)

    def delete_clip(self):
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            del self.clip_list[idx]
            self.refresh_tree()

    def refresh_tree(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for i, c in enumerate(self.clip_list):
            self.tree.insert("", tk.END, values=(i+1, c['start'], c['end'], c['name'], c['status']))

    def save_project(self):
        f = filedialog.asksaveasfilename(filetypes=[("JSON", "*.json")], defaultextension=".json")
        if f:
            with open(f, 'w', encoding='utf-8') as file:
                json.dump({"video": self.video_path.get(), "out": self.output_dir.get(), "clips": self.clip_list}, file, indent=4)
            messagebox.showinfo("提示", "保存成功")

    def load_project(self):
        f = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if f:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.video_path.set(data.get("video", ""))
                self.output_dir.set(data.get("out", ""))
                self.clip_list = data.get("clips", [])
                self.refresh_tree()

    def start_processing_thread(self):
        if not self.ffmpeg_path:
            messagebox.showerror("错误", "找不到 ffmpeg.exe，无法开始！")
            return
        if not self.clip_list:
            messagebox.showwarning("提示", "列表是空的")
            return
            
        self.run_btn.config(state="disabled")
        threading.Thread(target=self.process).start()

    def process(self):
        src = self.video_path.get()
        dst_dir = self.output_dir.get()
        if not os.path.exists(dst_dir): os.makedirs(dst_dir)
        
        total = len(self.clip_list)
        _, ext = os.path.splitext(src)
        
        for i, item in enumerate(self.clip_list):
            if item['status'] == "完成": continue
            
            out_name = f"{item['name']}{ext}"
            out_path = os.path.join(dst_dir, out_name)
            
            # 更新UI
            self.root.after(0, lambda idx=i: self.update_row(idx, "剪辑中..."))
            
            # 命令
            cmd = [
                self.ffmpeg_path, '-y',
                '-ss', item['start'],
                '-to', item['end'],
                '-i', src,
                '-c', 'copy',  # 关键：流复制
                '-avoid_negative_ts', '1',
                out_path
            ]
            
            # 执行
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, check=True)
                res = "完成"
            except Exception as e:
                res = "失败"
                print(e)
                
            self.root.after(0, lambda idx=i, s=res: self.update_row(idx, s))
            self.root.after(0, lambda v=(i+1)/total*100: self.progress.config(value=v))
        
        self.root.after(0, lambda: messagebox.showinfo("完成", "所有任务处理完毕"))
        self.root.after(0, lambda: self.run_btn.config(state="normal"))
        self.root.after(0, lambda: self.status_label.config(text="任务完成"))

    def update_row(self, idx, status):
        self.clip_list[idx]['status'] = status
        # 刷新单行显示
        item_id = self.tree.get_children()[idx]
        vals = list(self.tree.item(item_id, 'values'))
        vals[-1] = status
        self.tree.item(item_id, values=vals)

if __name__ == "__main__":
    if STYLE_THEME:
        root = ttk.Window(themename=STYLE_THEME)
    else:
        root = tk.Tk()
    app = VideoClipperApp(root)
    root.mainloop()