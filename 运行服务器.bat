@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title 电脑远程控制服务器管理
color 0A

set "SERVER_PORT=5002"
set "SERVER_TITLE=电脑远程控制服务器"
set "DEPS=Pillow psutil mss opencv-python numpy flask flask-socketio"
set "AUTOSTART_NAME=LAN-PC-Manager-Server"
set "AUTOSTART_SCRIPT=%~dp0启动服务器_静默.bat"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 警告：当前未以管理员身份运行！
    echo 建议以管理员身份运行此脚本以获得完整功能。
    echo.
    pause
)

cd /d "%~dp0"

python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo 未检测到Python，请先安装Python！
    pause
    exit /b 1
)

echo 正在检查依赖...
set "install_failed="
for %%d in (%DEPS%) do (
    pip show %%d >nul 2>&1
    if !errorLevel! neq 0 (
        echo 正在安装 %%d 库...
        pip install %%d >nul 2>&1
        if !errorLevel! neq 0 (
            echo [X] %%d 安装失败！
            set "install_failed=1"
        ) else (
            echo [OK] %%d 已安装
        )
    ) else (
        echo [OK] %%d 已安装
    )
)

if defined install_failed (
    echo.
    echo [警告] 部分依赖安装失败，服务器可能无法正常运行！
    echo 请检查网络连接或手动执行: pip install -r requirements.txt
    echo.
) else (
    echo.
    echo [OK] 所有依赖检查完成！
    echo.
)

:MENU
cls
call :CHECK_AUTOSTART_STATUS
echo. 
echo  ========================================================
echo                电脑远程控制服务器                
echo  ========================================================
echo  1. 启动/重启服务器                              
echo  2. 停止服务器                                  
echo  3. 查看服务器状态                              
echo  4. 安装/更新依赖                               
echo  5. 开机自启动设置                              
echo  6. 退出                                        
echo  ========================================================
echo. 
set /p choice=请输入操作编号（1-6）：

if "%choice%"=="1" goto START_SERVER
if "%choice%"=="2" goto STOP_SERVER
if "%choice%"=="3" goto CHECK_STATUS
if "%choice%"=="4" goto INSTALL_DEPENDENCIES
if "%choice%"=="5" goto AUTOSTART_MENU
if "%choice%"=="6" goto EXIT
echo 输入错误，请重新选择！
pause
goto MENU

:START_SERVER
echo 正在启动服务器...
call :KILL_PORT_PROCESS
start "%SERVER_TITLE%" cmd /k "python server.py"
timeout /t 2 >nul
echo 服务器已启动！
echo 访问地址：http://127.0.0.1:%SERVER_PORT%
pause
goto MENU

:STOP_SERVER
echo 正在停止服务器...
call :KILL_PORT_PROCESS
echo 完成。
pause
goto MENU

:CHECK_STATUS
echo 正在查询服务器状态...
netstat -ano | findstr ":%SERVER_PORT% " | findstr "LISTENING" >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] 服务器正在运行！
    echo 访问地址：http://127.0.0.1:%SERVER_PORT%
) else (
    echo [X] 服务器未运行！
)
pause
goto MENU

:INSTALL_DEPENDENCIES
echo 正在安装/更新依赖...
pip install --upgrade pip >nul 2>&1
for %%d in (%DEPS%) do (
    echo 正在更新 %%d ...
    pip install --upgrade %%d >nul 2>&1
    if !errorLevel! neq 0 (
        echo [X] %%d 更新失败！
    ) else (
        echo [OK] %%d 已更新
    )
)
echo 完成。
pause
goto MENU

:AUTOSTART_MENU
cls
call :CHECK_AUTOSTART_STATUS
echo.
echo  ==================== 开机自启动设置 ====================
echo.
if "%AUTOSTART_ENABLED%"=="1" (
    echo  当前状态: [已启用] 开机将自动启动服务器
) else (
    echo  当前状态: [已禁用] 开机不会自动启动服务器
)
echo.
echo  1. 启用开机自启动
echo  2. 禁用开机自启动
echo  3. 返回主菜单
echo.
set /p auto_choice=请选择操作（1-3）：

if "%auto_choice%"=="1" goto ENABLE_AUTOSTART
if "%auto_choice%"=="2" goto DISABLE_AUTOSTART
if "%auto_choice%"=="3" goto MENU
echo 输入错误，请重新选择！
pause
goto AUTOSTART_MENU

:ENABLE_AUTOSTART
echo 正在启用开机自启动...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "%AUTOSTART_NAME%" /t REG_SZ /d "\"%AUTOSTART_SCRIPT%\"" /f >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] 开机自启动已启用！
    echo 下次开机时服务器将自动在后台启动。
) else (
    echo [X] 启用失败，请尝试以管理员身份运行。
)
pause
goto AUTOSTART_MENU

:DISABLE_AUTOSTART
echo 正在禁用开机自启动...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "%AUTOSTART_NAME%" /f >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] 开机自启动已禁用！
) else (
    echo [X] 禁用失败或自启动项不存在。
)
pause
goto AUTOSTART_MENU

:CHECK_AUTOSTART_STATUS
set "AUTOSTART_ENABLED=0"
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "%AUTOSTART_NAME%" >nul 2>&1
if %errorLevel% equ 0 (
    set "AUTOSTART_ENABLED=1"
)
exit /b 0

:KILL_PORT_PROCESS
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%SERVER_PORT% " ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
exit /b 0

:EXIT
echo 感谢使用，再见！
exit /b 0
