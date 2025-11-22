# BatchClipFlow - 批量视频分段工具

## 软件主界面

![alt text](image.png)

## 结构说明

```
BatchClipFlow/
├── main.py                # 主程序代码
├── build.py               # 一键打包脚本
├── requirements.txt       # 依赖库列表
├── ffmpeg.exe             # [必须手动放入] 视频处理核心组件
├── app_config.json        # [自动生成] 记录上次打开的项目
├── screenshot.png         # [可选] 放入截图以在说明书中显示
└── README.md              # 项目说明书
```

## 1. 安装环境

请确保已安装 Python 和 FFmpeg。
运行安装依赖:

```
pip install -r requirements.txt
```

## 2. 使用方法

运行:

```
python main.py
```

## 3. 项目打包

```
python build.py
```
