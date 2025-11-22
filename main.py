import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu
import subprocess
import os
import json
import threading
import sys
import platform
import time

# --- 配置与美化 ---
# 尝试加载美化库，让界面更庄严整洁
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    STYLE_THEME = "cosmo" # 保持清爽风格
except ImportError:
    import tkinter.ttk as ttk
    STYLE_THEME = None

# 全局配置文件名
APP_CONFIG_FILE = "app_config.json"
DEFAULT_PROJECT_NAME = "default_project.json"

class VideoClipperApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1200x800")
        self.root.title("寺院视频剪辑管理系统 (TempleClipFlow)")
        
        self.ffmpeg_path = self.find_ffmpeg()
        
        # --- 核心状态 ---
        self.current_project_path = None 
        
        # --- 定制化：佛教寺院常用分类 ---
        self.default_categories = [
            "法师开示", 
            "经典讲座", 
            "法会记录", 
            "早晚课诵", 
            "义工活动", 
            "禅修剪影", 
            "参访交流",
            "其他素材"
        ]
        
        self.project_data = {
            "output_dir": "",
            "auto_subfolder": True,
            "videos": {},
            "categories": self.default_categories.copy() 
        }
        self.current_video_path = None
        
        # --- UI 变量 ---
        self.var_output_dir = tk.StringVar()
        self.var_auto_sub = tk.BooleanVar(value=True)
        
        # --- 构建界面 ---
        self.create_menu()
        self.setup_ui()
        
        # --- 初始化加载 ---
        self.check_environment()
        self.startup_load()

    def find_ffmpeg(self):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        
        local = os.path.join(base, "ffmpeg.exe")
        if platform.system() != "Windows": local = os.path.join(base, "ffmpeg")
        
        if os.path.exists(local): return local
        from shutil import which
        return which("ffmpeg")

    def check_environment(self):
        if self.ffmpeg_path:
            src = "本地" if "ffmpeg.exe" in self.ffmpeg_path else "系统"
            self.update_status(f"系统就绪 | FFmpeg组件来源: {src}", "green")
        else:
            self.update_status("未检测到FFmpeg组件，无法执行剪辑", "red")
            self.root.after(500, lambda: messagebox.showerror("组件缺失", "请将 ffmpeg.exe 放入软件目录中。"))

    # ===========================
    #      项目管理核心逻辑
    # ===========================
    
    def startup_load(self):
        """启动时读取全局配置，打开上次的项目"""
        last_project = None
        if os.path.exists(APP_CONFIG_FILE):
            try:
                with open(APP_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    last_project = config.get("last_opened_project")
            except:
                pass
        
        if not last_project or not os.path.exists(last_project):
            last_project = os.path.abspath(DEFAULT_PROJECT_NAME)
            
        self.load_project_file(last_project)

    def create_new_project(self):
        """新建弘法项目"""
        self.trigger_autosave()
        file_path = filedialog.asksaveasfilename(
            title="新建弘法项目",
            defaultextension=".json",
            filetypes=[("弘法项目文件", "*.json")],
            initialfile="新弘法项目.json"
        )
        
        if file_path:
            self.project_data = {
                "output_dir": "",
                "auto_subfolder": True,
                "videos": {},
                "categories": self.default_categories.copy()
            }
            self.current_video_path = None
            self.current_project_path = file_path
            self.trigger_autosave()
            self.refresh_ui_from_data()
            self.update_app_title()
            self.save_app_config()

    def open_project_dialog(self):
        file_path = filedialog.askopenfilename(
            title="打开项目",
            filetypes=[("弘法项目文件", "*.json")]
        )
        if file_path:
            self.load_project_file(file_path)

    def load_project_file(self, file_path):
        self.current_project_path = file_path
        if not os.path.exists(file_path):
            self.project_data = {
                "output_dir": "", 
                "auto_subfolder": True, 
                "videos": {},
                "categories": self.default_categories.copy()
            }
            self.trigger_autosave()
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "categories" not in data:
                        data["categories"] = self.default_categories.copy()
                    self.project_data = data
            except Exception as e:
                messagebox.showerror("错误", f"文件读取失败: {e}")
                return

        self.refresh_ui_from_data()
        self.update_app_title()
        self.save_app_config()
        self.update_status(f"当前项目: {os.path.basename(file_path)}")

    def save_app_config(self):
        config = {"last_opened_project": self.current_project_path}
        try:
            with open(APP_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except:
            pass

    def trigger_autosave(self, *args):
        if not self.current_project_path: return
        self.project_data["output_dir"] = self.var_output_dir.get()
        self.project_data["auto_subfolder"] = self.var_auto_sub.get()
        try:
            with open(self.current_project_path, 'w', encoding='utf-8') as f:
                json.dump(self.project_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.update_status(f"自动保存失败: {e}", "red")

    def update_app_title(self):
        name = os.path.basename(self.current_project_path) if self.current_project_path else "未命名"
        self.root.title(f"寺院视频剪辑管理系统 - {name}")

    # ===========================
    #      分类管理逻辑
    # ===========================
    
    def open_category_manager(self):
        """分类标签管理窗口"""
        win = tk.Toplevel(self.root)
        win.title("分类标签管理")
        win.geometry("400x500")
        
        frame_list = ttk.Frame(win, padding=10)
        frame_list.pack(fill=tk.BOTH, expand=True)
        
        lbl = ttk.Label(frame_list, text="当前分类标签:")
        lbl.pack(anchor="w", pady=(0,5))
        
        listbox = tk.Listbox(frame_list, font=("微软雅黑", 10), height=15)
        listbox.pack(fill=tk.BOTH, expand=True)
        
        current_cats = self.project_data.get("categories", [])
        for cat in current_cats:
            listbox.insert(tk.END, cat)
            
        frame_ops = ttk.Frame(win, padding=10)
        frame_ops.pack(fill=tk.X)
        
        entry_new = ttk.Entry(frame_ops)
        entry_new.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        
        def add_cat():
            val = entry_new.get().strip()
            if val and val not in listbox.get(0, tk.END):
                listbox.insert(tk.END, val)
                entry_new.delete(0, tk.END)
        
        def del_cat():
            sel = listbox.curselection()
            if sel:
                listbox.delete(sel[0])

        btn_add = ttk.Button(frame_ops, text="添加标签", command=add_cat)
        btn_add.pack(side=tk.LEFT)
        
        btn_del = ttk.Button(frame_ops, text="删除选中", command=del_cat, bootstyle="danger")
        btn_del.pack(side=tk.RIGHT)
        
        def save_cats():
            new_cats = list(listbox.get(0, tk.END))
            self.project_data["categories"] = new_cats
            self.trigger_autosave()
            self.ent_cat['values'] = new_cats
            if new_cats:
                if self.ent_cat.get() not in new_cats:
                     self.ent_cat.current(0)
            messagebox.showinfo("提示", "分类配置已更新！")
            win.destroy()
            
        ttk.Button(win, text="💾 保存更改", command=save_cats, bootstyle="success").pack(fill=tk.X, padx=10, pady=10)

    # ===========================
    #      UI 构建与交互
    # ===========================

    def create_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="📄 新建弘法项目", command=self.create_new_project)
        file_menu.add_command(label="📂 打开项目", command=self.open_project_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="❌ 退出系统", command=self.root.quit)
        
        setting_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=setting_menu)
        setting_menu.add_command(label="🏷️ 分类标签管理", command=self.open_category_manager)

    def setup_ui(self):
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- 左侧：视频列表 ---
        self.frame_left = ttk.Labelframe(self.paned, text="1. 视频素材列表", padding=5)
        self.paned.add(self.frame_left, weight=1)

        lf_btn = ttk.Frame(self.frame_left)
        lf_btn.pack(fill=tk.X, pady=5)
        ttk.Button(lf_btn, text="➕ 导入视频素材", command=self.import_videos, bootstyle="primary").pack(fill=tk.X)
        
        self.list_videos = tk.Listbox(self.frame_left, selectmode=tk.SINGLE, font=("微软雅黑", 10), bd=0, highlightthickness=1)
        self.list_videos.pack(fill=tk.BOTH, expand=True, pady=5)
        self.list_videos.bind('<<ListboxSelect>>', self.on_video_select)
        
        ttk.Button(self.frame_left, text="🗑 移除选中视频", command=self.remove_video).pack(fill=tk.X, pady=5)

        # --- 右侧：工作区 ---
        self.frame_right = ttk.Labelframe(self.paned, text="2. 剪辑工作台", padding=10)
        self.paned.add(self.frame_right, weight=4)

        # 全局设置
        frame_settings = ttk.Frame(self.frame_right)
        frame_settings.pack(fill=tk.X, pady=5)
        ttk.Label(frame_settings, text="输出位置:").pack(side=tk.LEFT)
        ttk.Entry(frame_settings, textvariable=self.var_output_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(frame_settings, text="选择文件夹...", command=self.select_output).pack(side=tk.LEFT)
        ttk.Checkbutton(frame_settings, text="自动按视频名建立文件夹", variable=self.var_auto_sub, command=self.trigger_autosave).pack(side=tk.LEFT, padx=10)

        # 表格
        cols = ("ID", "Start", "End", "Category", "Name", "Status")
        self.tree = ttk.Treeview(self.frame_right, columns=cols, show="headings", selectmode="browse", height=10)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)
        
        col_map = {"ID": "序号", "Start": "开始时间", "End": "结束时间", "Category": "分类标签", "Name": "输出文件名", "Status": "状态"}
        col_widths = [50, 100, 100, 100, 250, 80]
        for i, col in enumerate(cols):
            self.tree.heading(col, text=col_map[col])
            self.tree.column(col, width=col_widths[i], anchor="center" if col!="Name" else "w")

        # 编辑区
        frame_edit = ttk.LabelFrame(self.frame_right, text="添加剪辑片段", padding=10)
        frame_edit.pack(fill=tk.X)

        f_in = ttk.Frame(frame_edit)
        f_in.pack(fill=tk.X)
        
        ttk.Label(f_in, text="开始:").pack(side=tk.LEFT)
        self.ent_start = ttk.Entry(f_in, width=10); self.ent_start.pack(side=tk.LEFT, padx=5); self.ent_start.insert(0, "00:00:00")
        
        ttk.Label(f_in, text="结束:").pack(side=tk.LEFT)
        self.ent_end = ttk.Entry(f_in, width=10); self.ent_end.pack(side=tk.LEFT, padx=5); self.ent_end.insert(0, "00:00:10")
        
        ttk.Label(f_in, text="分类:").pack(side=tk.LEFT, padx=(10,0))
        self.ent_cat = ttk.Combobox(f_in, width=12, state="normal") 
        self.ent_cat.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(f_in, text="文件名:").pack(side=tk.LEFT, padx=(10,0))
        self.ent_name = ttk.Entry(f_in, width=20); self.ent_name.pack(side=tk.LEFT, padx=5)

        # 按钮区
        f_act = ttk.Frame(frame_edit)
        f_act.pack(fill=tk.X, pady=10)
        self.btn_add = ttk.Button(f_act, text="⬇ 确认添加 (Enter)", command=self.add_clip, state="disabled")
        self.btn_add.pack(side=tk.LEFT)
        self.root.bind('<Return>', lambda e: self.add_clip())
        
        ttk.Button(f_act, text="❌ 删除片段", command=self.del_clip).pack(side=tk.LEFT, padx=10)
        
        self.btn_run = ttk.Button(self.frame_right, text="🚀 开始批量处理 (导出所有视频)", command=self.start_processing, bootstyle="success")
        self.btn_run.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        self.lbl_status = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor="w")
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

    def update_status(self, text, color=None):
        self.lbl_status.config(text=text, foreground=color if color else "black")

    # ===========================
    #      业务逻辑
    # ===========================

    def refresh_ui_from_data(self):
        self.var_output_dir.set(self.project_data.get("output_dir", ""))
        self.var_auto_sub.set(self.project_data.get("auto_subfolder", True))
        
        cats = self.project_data.get("categories", self.default_categories)
        self.ent_cat['values'] = cats
        if cats: self.ent_cat.current(0)
        
        self.list_videos.delete(0, tk.END)
        self.current_video_path = None 
        self.refresh_clip_tree() 
        self.btn_add.config(state="disabled")
        
        for path in self.project_data["videos"].keys():
            self.list_videos.insert(tk.END, f"🎬 {os.path.basename(path)}")

    def import_videos(self):
        files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi *.flv *.ts")])
        if not files: return
        
        count = 0
        for f in files:
            f = f.replace("\\", "/")
            if f not in self.project_data["videos"]:
                self.project_data["videos"][f] = [] 
                count += 1
        
        if count > 0:
            if not self.var_output_dir.get():
                self.var_output_dir.set(os.path.dirname(files[0]))
            self.list_videos.delete(0, tk.END)
            for path in self.project_data["videos"].keys():
                self.list_videos.insert(tk.END, f"🎬 {os.path.basename(path)}")
            self.trigger_autosave()
            messagebox.showinfo("导入成功", f"已添加 {count} 个视频素材")

    def remove_video(self):
        sel = self.list_videos.curselection()
        if not sel: return
        keys = list(self.project_data["videos"].keys())
        if sel[0] < len(keys):
            del self.project_data["videos"][keys[sel[0]]]
            self.trigger_autosave()
            self.list_videos.delete(0, tk.END)
            for path in self.project_data["videos"].keys():
                self.list_videos.insert(tk.END, f"🎬 {os.path.basename(path)}")
            self.refresh_clip_tree()

    def on_video_select(self, event):
        sel = self.list_videos.curselection()
        if not sel: return
        keys = list(self.project_data["videos"].keys())
        if sel[0] < len(keys):
            self.current_video_path = keys[sel[0]]
            self.refresh_clip_tree()
            self.btn_add.config(state="normal")
            self.frame_right.config(text=f"2. 剪辑工作台 - 当前视频: {os.path.basename(self.current_video_path)}")

    def refresh_clip_tree(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        if not self.current_video_path: return
        
        clips = self.project_data["videos"].get(self.current_video_path, [])
        for i, c in enumerate(clips):
            self.tree.insert("", tk.END, values=(
                i+1, c['start'], c['end'], c.get('category',''), c['name'], c.get('status','等待')
            ))

    def add_clip(self):
        if not self.current_video_path or self.btn_add['state'] == 'disabled': return
        s, e = self.ent_start.get(), self.ent_end.get()
        cat, n = self.ent_cat.get(), self.ent_name.get()
        if not n: n = f"clip_{len(self.project_data['videos'][self.current_video_path])+1}"
        
        new_clip = {"start": s, "end": e, "category": cat, "name": n, "status": "等待"}
        self.project_data["videos"][self.current_video_path].append(new_clip)
        
        self.refresh_clip_tree()
        self.trigger_autosave()
        self.ent_start.delete(0, tk.END); self.ent_start.insert(0, e)
        self.ent_name.delete(0, tk.END)

    def del_clip(self):
        if not self.current_video_path: return
        sel = self.tree.selection()
        if sel:
            idx = self.tree.index(sel[0])
            del self.project_data["videos"][self.current_video_path][idx]
            self.refresh_clip_tree()
            self.trigger_autosave()

    def select_output(self):
        p = filedialog.askdirectory()
        if p: 
            self.var_output_dir.set(p)
            self.trigger_autosave()

    def start_processing(self):
        if not self.ffmpeg_path: return
        threading.Thread(target=self.process_all_thread).start()

    def process_all_thread(self):
        self.btn_run.config(state="disabled")
        base_out = self.var_output_dir.get()
        if not base_out:
            messagebox.showerror("错误", "请设置输出目录")
            self.btn_run.config(state="normal")
            return

        all_videos = self.project_data["videos"]
        total_clips = sum(len(v) for v in all_videos.values())
        processed = 0
        
        for vid_path, clips in all_videos.items():
            if not os.path.exists(vid_path): continue
            vid_name = os.path.splitext(os.path.basename(vid_path))[0]
            _, ext = os.path.splitext(vid_path)
            
            for clip in clips:
                if clip['status'] == "完成": 
                    processed += 1
                    continue
                
                final_dir = base_out
                if self.var_auto_sub.get(): final_dir = os.path.join(final_dir, vid_name)
                if clip.get('category'): final_dir = os.path.join(final_dir, clip['category'])
                
                if not os.path.exists(final_dir): os.makedirs(final_dir)
                out_path = os.path.join(final_dir, f"{clip['name']}{ext}")
                
                if self.current_video_path == vid_path:
                    self.root.after(0, lambda c=clip: self.update_row_status(c, "处理中..."))

                cmd = [self.ffmpeg_path, '-y', '-ss', clip['start'], '-to', clip['end'], '-i', vid_path, '-c', 'copy', '-avoid_negative_ts', '1', out_path]
                
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, check=True)
                    clip['status'] = "完成"
                except:
                    clip['status'] = "失败"
                
                processed += 1
                self.trigger_autosave() 
                if self.current_video_path == vid_path: self.root.after(0, self.refresh_clip_tree)
                self.update_status(f"处理进度: {processed}/{total_clips}")

        self.root.after(0, lambda: messagebox.showinfo("功德圆满", "所有视频处理完毕！"))
        self.root.after(0, lambda: self.btn_run.config(state="normal"))

    def update_row_status(self, clip_obj, status):
        clip_obj['status'] = status
        self.refresh_clip_tree()

if __name__ == "__main__":
    if STYLE_THEME:
        root = ttk.Window(themename=STYLE_THEME)
    else:
        root = tk.Tk()
    app = VideoClipperApp(root)
    root.mainloop()