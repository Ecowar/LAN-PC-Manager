# 🖥️ 电脑控制中心 (PC Remote Control)

基于 Web 的电脑远程管理工具，通过手机或浏览器即可远程控制电脑。

![版本](https://img.shields.io/badge/version-1.2.6-blue)
![Python](https://img.shields.io/badge/python-3.12+-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

## ✨ 功能特性

- **🔌 系统控制** - 关机、重启、休眠、锁屏、定时关机
- **⌨️ 命令执行** - 远程执行 CMD 命令，管理运行中的应用
- **📊 系统监控** - 实时查看 CPU、内存、磁盘、网络状态
- **🖥️ 屏幕画面** - MJPEG 实时流传输，支持画质/帧率调节
- **💬 消息中心** - 双向通信，支持弹窗回复
- **📁 文件管理** - 手机向电脑发送文件，流式传输不爆内存
- **📱 移动适配** - 响应式设计，完美支持手机端操作

## 🚀 快速开始

### 环境要求
- Windows 系统
- Python 3.7+
- Pillow
- psutil
- mss
- opencv-python
- numpy
### 安装运行

1. 克隆仓库
```bash
git clone https://github.com/Ecowar/PC-Remote-Control.git
```
2. 打开运行服务器.bat，会自动检测 Python 是否安装，自动安装缺失的依赖库
3. 启动 Web 服务并显示访问地址(默认密码为admin)
