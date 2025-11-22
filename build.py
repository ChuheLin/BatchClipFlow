import os
import shutil
import subprocess
import sys
import time

def build_exe():
    print("="*40)
    print("  开始构建：寺院视频剪辑管理系统")
    print("="*40)

    # 1. 检查并安装 PyInstaller
    try:
        import PyInstaller
        print("[1/4] 检测到 PyInstaller 已安装")
    except ImportError:
        print("[1/4] 正在安装打包工具 PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"])
        except Exception as e:
            print(f"安装失败，请手动运行: pip install pyinstaller")
            return

    # 2. 清理旧的构建文件
    print("[2/4] 清理旧文件...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
            except:
                pass
    if os.path.exists("TempleClipFlow.spec"):
        try:
            os.remove("TempleClipFlow.spec")
        except:
            pass

    # 3. 执行打包命令
    # --noconsole: 隐藏黑色弹窗
    # --onefile: 生成单个文件
    # --collect-all: 强制收集 ttkbootstrap 的主题文件（关键）
    print("[3/4] 正在打包 (可能需要 1-2 分钟)...")
    
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--name=寺院视频剪辑系统",
        "--collect-all=ttkbootstrap", 
        "main.py"
    ]
    
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        print("❌ 打包出错！请检查上方报错信息。")
        input("按回车键退出...")
        return

    # 4. 自动复制 ffmpeg.exe
    print("[4/4] 处理依赖组件...")
    ffmpeg_src = "ffmpeg.exe"
    dist_folder = "dist"
    
    if os.path.exists(ffmpeg_src):
        shutil.copy(ffmpeg_src, os.path.join(dist_folder, ffmpeg_src))
        print("✅ 已将 ffmpeg.exe 复制到软件目录")
    else:
        print("⚠️  警告：当前目录下未找到 ffmpeg.exe")
        print("   请务必手动将 ffmpeg.exe 放入 dist 文件夹，否则软件无法运行！")

    print("\n" + "="*40)
    print("🎉 打包成功！")
    print(f"软件位置: {os.path.abspath(dist_folder)}")
    print("="*40)
    
    # 自动打开文件夹
    try:
        os.startfile(dist_folder)
    except:
        pass

if __name__ == "__main__":
    build_exe()
    input("\n按回车键退出...")