@echo off
chcp 65001 >nul
title 电脑远程控制服务器管理
color 0A

:: 检查是否以管理员身份运行
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 警告：当前未以管理员身份运行！
    echo 建议以管理员身份运行此脚本以获得完整功能。
    echo.
    pause
)

:: 进入脚本所在目录
cd /d "%~dp0"

:: 检查Python是否安装
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo 未检测到Python，请先安装Python！
    pause
    exit /b 1
)

:: 检查依赖是否安装
echo SafeMode
echo 正在检查依赖...
pip show Pillow >nul 2>&1
if %errorLevel% neq 0 (
    echo 正在安装Pillow库...
    pip install Pillow >nul 2>&1
    echo [OK] Pillow已安装
) else (
    echo [OK] Pillow已安装
)

pip show psutil >nul 2>&1
if %errorLevel% neq 0 (
    echo 正在安装psutil库...
    pip install psutil >nul 2>&1
    echo [OK] psutil已安装
) else (
    echo [OK] psutil已安装
)

pip show mss >nul 2>&1
if %errorLevel% neq 0 (
    echo 正在安装mss库...
    pip install mss >nul 2>&1
    echo [OK] mss已安装
) else (
    echo [OK] mss已安装
)

pip show opencv-python >nul 2>&1
if %errorLevel% neq 0 (
    echo 正在安装opencv-python库...
    pip install opencv-python >nul 2>&1
    echo [OK] opencv-python已安装
) else (
    echo [OK] opencv-python已安装
)

pip show numpy >nul 2>&1
if %errorLevel% neq 0 (
    echo 正在安装numpy库...
    pip install numpy >nul 2>&1
    echo [OK] numpy已安装
) else (
    echo [OK] numpy已安装
)

pip show flask >nul 2>&1
if %errorLevel% neq 0 (
    echo 正在安装flask库...
    pip install flask >nul 2>&1
    echo [OK] flask已安装
) else (
    echo [OK] flask已安装
)

pip show flask-socketio >nul 2>&1
if %errorLevel% neq 0 (
    echo 正在安装flask-socketio库...
    pip install flask-socketio >nul 2>&1
    echo [OK] flask-socketio已安装
) else (
    echo [OK] flask-socketio已安装
)

echo.
echo [OK] 所有依赖检查完成！
echo.

:MENU
cls
echo. 
echo  ========================================================
echo                电脑远程控制服务器                
echo  ========================================================
echo  1. 启动/重启服务器                              
echo  2. 停止服务器                                  
echo  3. 查看服务器状态                              
echo  4. 安装/更新依赖                               
echo  5. 退出                                        
echo  ========================================================
echo. 
set /p choice=请输入操作编号（1-5）：

if "%choice%"=="1" goto START_SERVER
if "%choice%"=="2" goto STOP_SERVER
if "%choice%"=="3" goto CHECK_STATUS
if "%choice%"=="4" goto INSTALL_DEPENDENCIES
if "%choice%"=="5" goto EXIT
echo 输入错误，请重新选择！
pause
goto MENU

:START_SERVER
echo 正在启动服务器...
:: 先停止占用5002端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5002') do (
    taskkill /f /pid %%a >nul 2>&1
)
start "电脑远程控制服务器" cmd /k "python server.py"
echo 服务器已启动！
echo 访问地址：http://127.0.0.1:5002
pause
goto MENU

:STOP_SERVER
echo 正在停止服务器...
:: 查找占用5000端口的进程并终止
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000') do (
    taskkill /f /pid %%a >nul 2>&1
)
taskkill /F /IM python.exe /IM pythonw.exe
echo 完成。
pause
goto MENU

:CHECK_STATUS
echo 正在查询服务器状态...
netstat -ano | findstr :5002 >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] 服务器正在运行！
    echo 访问地址：http://127.0.0.1:5002
) else (
    echo [X] 服务器未运行！
)
pause
goto MENU

:INSTALL_DEPENDENCIES
echo 正在安装/更新依赖...
pip install --upgrade pip >nul 2>&1
pip install psutil wmi Pillow mss opencv-python numpy flask flask-socketio
echo 完成。
pause
goto MENU

:EXIT
echo 感谢使用，再见！
exit /b 0
