from flask import Flask, request, jsonify, send_file, Response, abort
import os
import subprocess
import ctypes
import psutil
import datetime
import io
import time
import cv2
import numpy as np
from mss import mss
from PIL import ImageGrab
import uuid
import shutil
import sys

app = Flask(__name__)

# 内存中的日志列表
LOGS = []
MAX_LOGS = 500  # 最大日志条数

# 内存中的消息历史记录
MESSAGE_HISTORY = []
MAX_MESSAGES = 100  # 最大消息条数

# 文件管理相关配置
MAX_UPLOAD_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
MAX_TEMP_STORAGE = 5 * 1024 * 1024 * 1024  # 5GB
TEMP_DIR = 'temp'
FILE_EXPIRY_TIME = 24 * 60 * 60  # 24小时

# 内存中的文件状态记录
# 存储文件元信息，不含内容
FILE_STATUS = {}

# 创建临时目录
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# 程序启动时清空临时目录
for file in os.listdir(TEMP_DIR):
    try:
        os.remove(os.path.join(TEMP_DIR, file))
    except Exception as e:
        log_action('清理临时文件失败', str(e))


# 日志记录函数
def log_action(action, details=''):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f'[{timestamp}] {action}'
    if details:
        log_entry += f' - {details}'
    
    # 添加到内存日志列表
    LOGS.insert(0, log_entry)  # 最新的日志放在前面
    
    # 限制日志数量
    if len(LOGS) > MAX_LOGS:
        LOGS.pop()  # 删除最旧的日志



@app.route('/')
def index():
    return send_file('index.html')

@app.route('/timer')
def timer():
    s = request.args.get('s', '60')
    os.system(f'shutdown /s /t {s}')
    log_action('设置定时关机', f'{s}秒后')
    return 'ok'

@app.route('/shutdown')
def shutdown():
    os.system('shutdown /s /t 0')
    log_action('执行立即关机')
    return 'ok'

@app.route('/restart')
def restart():
    os.system('shutdown /r /t 0')
    log_action('执行重启电脑')
    return 'ok'

@app.route('/sleep')
def sleep():
    os.system('rundll32 powrprof.dll,SetSuspendState 0,1,0')
    log_action('执行休眠')
    return 'ok'

@app.route('/lock')
def lock():
    ctypes.windll.user32.LockWorkStation()
    log_action('执行锁屏')
    return 'ok'

@app.route('/abort')
def abort():
    os.system('shutdown /a')
    log_action('取消关机')
    return 'ok'

# 定义Windows API函数
user32 = ctypes.windll.user32

@app.route('/run')
def run():
    cmd = request.args.get('cmd','')
    if cmd:
        subprocess.Popen(cmd, shell=True)
        log_action('执行命令', cmd)
    return 'ok'

@app.route('/running_apps')
def running_apps():
    log_action('获取运行应用列表')
    try:
        apps = []
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name']:
                apps.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name']
                })
        # 按应用名称排序
        apps.sort(key=lambda x: x['name'])
        return jsonify({'success': True, 'apps': apps[:100]})  # 限制返回前100个应用
    except Exception as e:
        log_action('获取运行应用列表失败', str(e))
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stop_app')
def stop_app():
    app_name = request.args.get('name', '')
    if app_name:
        log_action('停止应用', app_name)
        try:
            # 尝试停止所有匹配的进程
            success = False
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] == app_name:
                    proc.terminate()
                    success = True
            if success:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': '未找到指定应用'})
        except Exception as e:
            log_action('停止应用失败', str(e))
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': '应用名称不能为空'})

@app.route('/sysinfo')
def sysinfo():
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    memory_used = round(memory.used / 1024 / 1024 / 1024, 2)
    memory_total = round(memory.total / 1024 / 1024 / 1024, 2)
    disk = psutil.disk_usage('/')
    disk_percent = disk.percent
    disk_used = round(disk.used / 1024 / 1024 / 1024, 2)
    disk_total = round(disk.total / 1024 / 1024 / 1024, 2)
    net_io = psutil.net_io_counters()
    bytes_sent = round(net_io.bytes_sent / 1024 / 1024, 2)
    bytes_recv = round(net_io.bytes_recv / 1024 / 1024, 2)
    boot_time = psutil.boot_time()
    boot_time_str = datetime.datetime.fromtimestamp(boot_time).strftime('%Y-%m-%d %H:%M:%S')
    load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
    
    log_action('获取系统信息')
    
    return jsonify({
        'cpu_percent': cpu_percent,
        'memory': {
            'percent': memory_percent,
            'used': memory_used,
            'total': memory_total
        },
        'disk': {
            'percent': disk_percent,
            'used': disk_used,
            'total': disk_total
        },
        'network': {
            'bytes_sent': bytes_sent,
            'bytes_recv': bytes_recv
        },
        'system': {
            'boot_time': boot_time_str,
            'load_avg': load_avg
        }
    })

@app.route('/syslog')
def syslog():
    log_action('获取系统日志')
    try:
        # 格式化日志输出为HTML
        html_output = ''
        for log in LOGS:
            if log.strip():
                # 为不同类型的日志添加不同的样式
                if '执行命令' in log:
                    html_output += f'<div style="color: #007bff; margin-bottom: 4px;">{log.strip()}</div>'
                elif '关机' in log or '重启' in log or '休眠' in log or '锁屏' in log:
                    html_output += f'<div style="color: #dc3545; margin-bottom: 4px;">{log.strip()}</div>'
                elif '系统信息' in log or '系统日志' in log:
                    html_output += f'<div style="color: #28a745; margin-bottom: 4px;">{log.strip()}</div>'
                else:
                    html_output += f'<div style="margin-bottom: 4px;">{log.strip()}</div>'
        if not html_output:
            html_output = '<div>暂无日志记录</div>'
        return html_output
    except Exception as e:
        return f'<div style="color: red;">获取日志失败: {str(e)}</div>'

@app.route('/screenshot')
def screenshot():
    log_action('获取屏幕截图')
    try:
        screenshot = ImageGrab.grab()
        img_io = io.BytesIO()
        screenshot.save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')
    except Exception as e:
        log_action('获取屏幕截图失败', str(e))
        return send_file(io.BytesIO(), mimetype='image/png')

# MJPEG 流路由
@app.route('/stream')
def stream():
    # 获取 URL 参数
    quality = request.args.get('quality', 'high')
    fps = int(request.args.get('fps', 24))
    
    log_action(f'开始 MJPEG 流 - 画质: {quality}, 帧率: {fps}')
    
    # 根据画质设置 JPEG 编码质量
    quality_map = {
        'low': 30,
        'medium': 60,
        'high': 80
    }
    jpeg_quality = quality_map.get(quality, 80)
    
    # 根据帧率计算帧间隔
    frame_interval = 1.0 / fps if fps > 0 else 0.0417  # 默认 24fps
    
    def generate():
        try:
            while True:
                # 抓取屏幕
                screenshot = ImageGrab.grab()
                # 转换为 JPEG
                img_io = io.BytesIO()
                screenshot.save(img_io, 'JPEG', quality=jpeg_quality)
                img_io.seek(0)
                # 发送边界和头部
                yield (b'--frame\r\n' 
                       b'Content-Type: image/jpeg\r\n' 
                       b'Content-Length: ' + str(len(img_io.getvalue())).encode() + b'\r\n' 
                       b'\r\n')
                # 发送图像数据
                yield img_io.getvalue()
                yield b'\r\n'
                # 控制帧率
                time.sleep(frame_interval)
        except Exception as e:
            log_action('MJPEG 流错误', str(e))
            pass
    
    # 返回 MJPEG 响应
    response = Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    return response

@app.route('/send_message')
def send_message():
    msg = request.args.get('msg', '')
    if msg:
        try:
            log_action('发送消息到电脑', msg)
            
            # 立即显示消息框，不等待用户回复
            def show_message_box():
                try:
                    # 尝试使用PowerShell创建图形化输入框
                    powershell_command = '''
                    Add-Type -AssemblyName System.Windows.Forms
                    
                    # 创建表单
                    $form = New-Object System.Windows.Forms.Form
                    $form.Text = "来自Web控制中心的消息"
                    $form.Width = 400
                    $form.Height = 300
                    $form.StartPosition = "CenterScreen"
                    $form.TopMost = $true
                    
                    # 创建消息标签
                    $messageLabel = New-Object System.Windows.Forms.Label
                    $messageLabel.Text = "消息内容:"
                    $messageLabel.Location = New-Object System.Drawing.Point(10, 10)
                    $messageLabel.Width = 380
                    $messageLabel.Font = New-Object System.Drawing.Font("Arial", 10, [System.Drawing.FontStyle]::Bold)
                    $form.Controls.Add($messageLabel)
                    
                    # 创建消息内容文本框
                    $messageTextBox = New-Object System.Windows.Forms.TextBox
                    $messageTextBox.Multiline = $true
                    $messageTextBox.ReadOnly = $true
                    $messageTextBox.Text = "PLACEHOLDER_MESSAGE"
                    $messageTextBox.Location = New-Object System.Drawing.Point(10, 30)
                    $messageTextBox.Width = 380
                    $messageTextBox.Height = 100
                    $messageTextBox.Font = New-Object System.Drawing.Font("Arial", 10)
                    $messageTextBox.ScrollBars = "Vertical"
                    $form.Controls.Add($messageTextBox)
                    
                    # 创建回复标签
                    $replyLabel = New-Object System.Windows.Forms.Label
                    $replyLabel.Text = "回复:"
                    $replyLabel.Location = New-Object System.Drawing.Point(10, 140)
                    $replyLabel.Width = 380
                    $replyLabel.Font = New-Object System.Drawing.Font("Arial", 10, [System.Drawing.FontStyle]::Bold)
                    $form.Controls.Add($replyLabel)
                    
                    # 创建回复输入框
                    $replyTextBox = New-Object System.Windows.Forms.TextBox
                    $replyTextBox.Location = New-Object System.Drawing.Point(10, 160)
                    $replyTextBox.Width = 380
                    $replyTextBox.Font = New-Object System.Drawing.Font("Arial", 10)
                    $form.Controls.Add($replyTextBox)
                    
                    # 创建确定按钮
                    $okButton = New-Object System.Windows.Forms.Button
                    $okButton.Text = "确定"
                    $okButton.Location = New-Object System.Drawing.Point(210, 190)
                    $okButton.Width = 80
                    $okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
                    $form.Controls.Add($okButton)
                    
                    # 创建取消按钮
                    $cancelButton = New-Object System.Windows.Forms.Button
                    $cancelButton.Text = "取消"
                    $cancelButton.Location = New-Object System.Drawing.Point(300, 190)
                    $cancelButton.Width = 80
                    $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
                    $form.Controls.Add($cancelButton)
                    
                    # 设置默认按钮
                    $form.AcceptButton = $okButton
                    $form.CancelButton = $cancelButton
                    
                    # 显示表单并获取结果
                    $result = $form.ShowDialog()
                    
                    # 获取回复内容
                    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
                        $reply = $replyTextBox.Text
                        if ([string]::IsNullOrEmpty($reply)) {
                            "用户未输入回复"
                        } else {
                            $reply
                        }
                    } else {
                        "用户取消了回复"
                    }
                    '''
                    
                    # 替换消息占位符
                    powershell_command = powershell_command.replace("PLACEHOLDER_MESSAGE", msg)
                    
                    # 执行PowerShell命令
                    process = subprocess.Popen(
                        ['powershell', '-Command', powershell_command],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        creationflags=0x08000000  # CREATE_NO_WINDOW
                    )
                    
                    # 获取输出
                    stdout, stderr = process.communicate()
                    
                    if stderr:
                        log_action('PowerShell执行有错误', stderr)
                    
                    # 获取回复结果
                    reply_result = stdout.strip()
                    
                    if not reply_result:
                        reply_result = "用户未输入回复"
                    
                    log_action('PowerShell输入框获取回复成功', f'回复: {reply_result}')
                    
                except Exception as ps_error:
                    # 如果PowerShell失败，尝试使用备用方案
                    log_action('PowerShell失败，使用备用方案', str(ps_error))
                    
                    # 首先显示消息
                    MB_OK = 0x00000000
                    MB_ICONINFORMATION = 0x00000040
                    
                    user32.MessageBoxW(
                        None,  # 父窗口句柄
                        msg,  # 消息内容
                        "来自Web控制中心的消息",  # 标题
                        MB_OK | MB_ICONINFORMATION
                    )
                    
                    reply_result = "用户查看了消息（无回复）"
                
                # 记录回复
                reply_message = {
                    'timestamp': datetime.datetime.now().isoformat(),
                    'type': 'received',
                    'content': reply_result
                }
                MESSAGE_HISTORY.insert(0, reply_message)
                
                # 限制消息数量
                if len(MESSAGE_HISTORY) > MAX_MESSAGES:
                    MESSAGE_HISTORY.pop()
                
                # 发送 SSE 消息给所有连接的客户端
                import json
                message_data = json.dumps({'type': 'new_message', 'message': reply_message})
                print(f"准备发送回复消息: {message_data}")
                send_to_all(message_data)
                print(f"回复消息已发送，当前连接数: {len(clients)}")
            
            # 异步执行消息框显示
            import threading
            thread = threading.Thread(target=show_message_box)
            thread.daemon = True
            thread.start()
            
            # 记录发送的消息
            MESSAGE_HISTORY.insert(0, {
                'timestamp': datetime.datetime.now().isoformat(),
                'type': 'sent',
                'content': msg
            })
            
            # 限制消息数量
            if len(MESSAGE_HISTORY) > MAX_MESSAGES:
                MESSAGE_HISTORY.pop()
            
            # 立即返回成功，不等待用户回复
            return jsonify({'success': True, 'reply': '消息已发送，电脑端已弹出消息框'})
        except Exception as e:
            log_action('发送消息失败', str(e))
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': '消息内容不能为空'})

@app.route('/message_history')
def message_history():
    log_action('获取消息历史记录')
    try:
        return jsonify({'success': True, 'messages': MESSAGE_HISTORY[:50]})  # 限制返回前50条消息
    except Exception as e:
        log_action('获取消息历史失败', str(e))
        return jsonify({'success': False, 'error': str(e)})

# SSE 连接管理
clients = []

# 发送消息给所有 SSE 客户端
def send_to_all(message):
    # 直接打印消息，用于调试
    print(f"发送消息: {message}")
    # 发送消息给所有连接的客户端
    for client in clients:
        try:
            # 发送消息
            client.put(message)
        except:
            # 如果发送失败，移除客户端
            if client in clients:
                clients.remove(client)

# SSE 客户端类
class SSEClient:
    def __init__(self):
        self.queue = []
    
    def put(self, message):
        self.queue.append(message)
    
    def get(self):
        if self.queue:
            return self.queue.pop(0)
        return None
    
    def has_message(self):
        return len(self.queue) > 0

# 获取临时文件路径
def get_file_path(file_id):
    return os.path.join(TEMP_DIR, f"{file_id}.tmp")

# 检查临时存储使用情况
def get_temp_storage_usage():
    total_size = 0
    for root, dirs, files in os.walk(TEMP_DIR):
        for f in files:
            try:
                total_size += os.path.getsize(os.path.join(root, f))
            except:
                pass
    return total_size

# 清理临时文件
def cleanup_temp_files():
    try:
        current_time = datetime.datetime.now().timestamp()
        total_removed = 0
        
        for file in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, file)
            try:
                # 检查文件是否超过过期时间
                if os.path.isfile(file_path):
                    file_mtime = os.path.getmtime(file_path)
                    if current_time - file_mtime > FILE_EXPIRY_TIME:
                        os.remove(file_path)
                        total_removed += 1
            except Exception as e:
                log_action('清理临时文件失败', str(e))
        
        if total_removed > 0:
            log_action('清理临时文件', f'删除了 {total_removed} 个过期文件')
    except Exception as e:
        log_action('清理临时文件任务失败', str(e))

# 启动定期清理任务
def start_cleanup_task():
    import threading
    def cleanup_task():
        while True:
            cleanup_temp_files()
            time.sleep(3600)  # 每小时执行一次
    
    thread = threading.Thread(target=cleanup_task)
    thread.daemon = True
    thread.start()

# 流式传输文件到客户端
def stream_file_to_client(file_path, save_path):
    try:
        # 检查目标目录是否存在，不存在则创建
        save_dir = os.path.dirname(save_path)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # 分块读取文件并写入
        chunk_size = 64 * 1024  # 64KB
        total_size = os.path.getsize(file_path)
        transferred = 0
        
        # 尝试直接写入文件
        try:
            with open(file_path, 'rb') as src, open(save_path, 'wb') as dst:
                while True:
                    chunk = src.read(chunk_size)
                    if not chunk:
                        break
                    dst.write(chunk)
                    transferred += len(chunk)
                    
                    # 计算进度并推送
                    if total_size > 0:
                        percent = int((transferred / total_size) * 100)
                        # 每1%推送一次进度
                        if percent % 1 == 0:
                            send_file_progress_update(os.path.splitext(os.path.basename(file_path))[0], percent)
        except PermissionError:
            # 权限错误，使用PowerShell命令以管理员权限写入文件
            # 构建PowerShell命令，使用流式写入
            powershell_command = '''
            $sourcePath = "PLACEHOLDER_SOURCE"
            $targetPath = "PLACEHOLDER_TARGET"
            
            # 确保目标目录存在
            $targetDir = Split-Path -Path $targetPath -Parent
            if (-not (Test-Path -Path $targetDir)) {
                New-Item -ItemType Directory -Path $targetDir -Force
            }
            
            # 流式复制文件
            $chunkSize = 65536
            $reader = [System.IO.File]::OpenRead($sourcePath)
            $writer = [System.IO.File]::Create($targetPath)
            $buffer = New-Object byte[] $chunkSize
            $totalSize = $reader.Length
            $transferred = 0
            
            try {
                while (($bytesRead = $reader.Read($buffer, 0, $buffer.Length)) -gt 0) {
                    $writer.Write($buffer, 0, $bytesRead)
                    $transferred += $bytesRead
                }
            } finally {
                $reader.Dispose()
                $writer.Dispose()
            }
            '''
            
            # 替换占位符
            powershell_command = powershell_command.replace('PLACEHOLDER_SOURCE', file_path.replace('"', '\"'))
            powershell_command = powershell_command.replace('PLACEHOLDER_TARGET', save_path.replace('"', '\"'))
            
            process = subprocess.Popen(
                ['powershell', '-Command', powershell_command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            
            stdout, stderr = process.communicate()
            if stderr:
                raise Exception(f'权限提升失败: {stderr}')
        
        return True
    except Exception as e:
        log_action('文件流式传输失败', str(e))
        return False

# 发送文件进度更新
def send_file_progress_update(file_id, percent):
    if file_id in FILE_STATUS:
        import json
        message = json.dumps({
            'type': 'file_progress',
            'file_id': file_id,
            'percent': percent
        })
        send_to_all(message)

# 文件上传API
@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'})
        
        # 检查文件类型（禁止执行文件）
        executable_extensions = ['.exe', '.bat', '.cmd', '.com', '.msi', '.ps1', '.js', '.vbs']
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext in executable_extensions:
            return jsonify({'success': False, 'error': 'Executable files are not allowed'})
        
        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置文件指针
        
        if file_size > MAX_UPLOAD_SIZE:
            return jsonify({'success': False, 'error': 'File too large'})
        
        # 检查临时存储使用情况
        temp_usage = get_temp_storage_usage()
        if temp_usage + file_size > MAX_TEMP_STORAGE:
            return jsonify({'success': False, 'error': 'Storage limit exceeded'})
        
        # 生成唯一ID
        unique_id = str(uuid.uuid4())
        file_path = get_file_path(unique_id)
        
        # 保存文件到临时目录
        file.save(file_path)
        
        # 记录文件状态
        file_info = {
            'id': unique_id,
            'name': file.filename,
            'size': format_file_size(file_size),
            'size_bytes': file_size,
            'path': file_path,  # 存储文件路径
            'status': 'pending',  # pending, transferring, completed, rejected
            'upload_time': datetime.datetime.now().timestamp(),
            'last_update': datetime.datetime.now().timestamp(),
            'transferred_bytes': 0
        }
        
        FILE_STATUS[unique_id] = file_info
        
        # 记录日志
        log_action('文件上传', f'{file.filename} ({file_info["size"]})')
        
        # 异步通知电脑端
        import threading
        thread = threading.Thread(target=notify_file_received, args=(file_info,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'file_id': unique_id, 'file_name': file.filename})
    except Exception as e:
        log_action('文件上传失败', str(e))
        return jsonify({'success': False, 'error': str(e)})

# 获取最近发送的文件列表
@app.route('/recent_files')
def recent_files():
    try:
        # 获取最近的文件，按上传时间排序
        recent_files = []
        for file_id, file_info in FILE_STATUS.items():
            recent_files.append({
                'id': file_id,
                'name': file_info['name'],
                'size': file_info['size'],
                'status': file_info['status'],
                'upload_time': file_info['upload_time']
            })
        
        # 按上传时间倒序排序
        recent_files.sort(key=lambda x: x['upload_time'], reverse=True)
        
        # 只返回最近10个文件
        return jsonify({'success': True, 'files': recent_files[:10]})
    except Exception as e:
        log_action('获取最近文件失败', str(e))
        return jsonify({'success': False, 'error': str(e)})

# 格式化文件大小
def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"

# 通知电脑端收到文件
def notify_file_received(file_info):
    try:
        log_action('通知电脑端接收文件', file_info['name'])
        
        # 创建PowerShell命令显示文件接收弹窗
        powershell_command = '''
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        
        # 创建表单
        $form = New-Object System.Windows.Forms.Form
        $form.Text = "📥 收到文件"
        $form.Width = 400
        $form.Height = 200
        $form.StartPosition = "CenterScreen"
        $form.TopMost = $true
        $form.FormBorderStyle = "FixedDialog"
        $form.MaximizeBox = $false
        
        # 创建文件图标
        $icon = New-Object System.Drawing.Icon([System.Drawing.SystemIcons]::Information, 32, 32)
        $form.Icon = $icon
        
        # 创建消息标签
        $messageLabel = New-Object System.Windows.Forms.Label
        $messageLabel.Text = "名称: ''' + file_info['name'] + '''"
        $messageLabel.Location = New-Object System.Drawing.Point(10, 30)
        $messageLabel.Width = 380
        $messageLabel.Font = New-Object System.Drawing.Font("Arial", 10)
        $form.Controls.Add($messageLabel)
        
        # 创建大小标签
        $sizeLabel = New-Object System.Windows.Forms.Label
        $sizeLabel.Text = "大小: ''' + file_info['size'] + '''"
        $sizeLabel.Location = New-Object System.Drawing.Point(10, 50)
        $sizeLabel.Width = 380
        $sizeLabel.Font = New-Object System.Drawing.Font("Arial", 10)
        $form.Controls.Add($sizeLabel)
        
        # 创建按钮容器
        $buttonPanel = New-Object System.Windows.Forms.Panel
        $buttonPanel.Location = New-Object System.Drawing.Point(10, 90)
        $buttonPanel.Width = 380
        $buttonPanel.Height = 60
        $form.Controls.Add($buttonPanel)
        
        # 创建接收按钮
        $acceptButton = New-Object System.Windows.Forms.Button
        $acceptButton.Text = "接收"
        $acceptButton.Location = New-Object System.Drawing.Point(100, 10)
        $acceptButton.Width = 80
        $acceptButton.DialogResult = [System.Windows.Forms.DialogResult]::Yes
        $buttonPanel.Controls.Add($acceptButton)
        
        # 创建拒绝按钮
        $rejectButton = New-Object System.Windows.Forms.Button
        $rejectButton.Text = "拒绝"
        $rejectButton.Location = New-Object System.Drawing.Point(200, 10)
        $rejectButton.Width = 80
        $rejectButton.DialogResult = [System.Windows.Forms.DialogResult]::No
        $buttonPanel.Controls.Add($rejectButton)
        
        # 设置默认按钮
        $form.AcceptButton = $acceptButton
        $form.CancelButton = $rejectButton
        
        # 播放提示音
        [System.Media.SystemSounds]::Information.Play()
        
        # 显示表单并获取结果
        $result = $form.ShowDialog()
        
        # 返回结果
        if ($result -eq [System.Windows.Forms.DialogResult]::Yes) {
            "accept"
        } else {
            "reject"
        }
        '''
        
        # 执行PowerShell命令
        process = subprocess.Popen(
            ['powershell', '-Command', powershell_command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        
        # 获取输出
        stdout, stderr = process.communicate()
        result = stdout.strip().lower()
        
        if result == 'accept':
            # 用户点击接收，打开文件保存对话框
            save_path = show_save_dialog(file_info['name'])
            if save_path:
                # 更新文件状态为传输中
                FILE_STATUS[file_info['id']]['status'] = 'transferring'
                FILE_STATUS[file_info['id']]['last_update'] = datetime.datetime.now().timestamp()
                
                # 发送状态更新通知
                send_file_status_update(file_info['id'], 'transferring')
                
                # 开始下载文件
                download_file(file_info, save_path)
            else:
                # 用户取消保存
                reject_file(file_info['id'])
        else:
            # 用户拒绝
            reject_file(file_info['id'])
            
    except Exception as e:
        log_action('通知电脑端失败', str(e))
        # 发生错误时拒绝文件
        if file_info['id'] in FILE_STATUS:
            reject_file(file_info['id'])
# 显示保存文件对话框
def show_save_dialog(default_name):
    try:
        # 使用字符串拼接避免f-string中的大括号冲突
        powershell_command = '''
        Add-Type -AssemblyName System.Windows.Forms
        
        # 创建保存文件对话框
        $saveDialog = New-Object System.Windows.Forms.SaveFileDialog
        $saveDialog.FileName = "''' + default_name + '''"
        $saveDialog.Title = "保存文件"
        $saveDialog.Filter = "All Files (*.*)|*.*"
        
        # 显示对话框
        $result = $saveDialog.ShowDialog()
        
        # 返回选择的路径
        if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
            $saveDialog.FileName
        } else {
            ""
        }
        '''
        
        # 执行PowerShell命令
        process = subprocess.Popen(
            ['powershell', '-Command', powershell_command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        
        # 获取输出
        stdout, stderr = process.communicate()
        return stdout.strip()
    except Exception as e:
        log_action('显示保存对话框失败', str(e))
        return None

# 检查是否以管理员权限运行
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# 请求管理员权限提升
def run_as_admin():
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, __file__, None, 1
        )
        return True
    except:
        return False

# 下载文件
def download_file(file_info, save_path):
    try:
        file_id = file_info['id']
        file_path = file_info['path']
        
        # 使用流式传输
        success = stream_file_to_client(file_path, save_path)
        
        if success:
            # 更新文件状态为已完成
            FILE_STATUS[file_id]['status'] = 'completed'
            FILE_STATUS[file_id]['last_update'] = datetime.datetime.now().timestamp()
            
            # 发送状态更新通知
            send_file_status_update(file_id, 'completed')
            
            # 记录日志
            log_action('文件接收完成', f'{file_info["name"]} -> {save_path}')
        else:
            raise Exception('文件传输失败')
        
    except Exception as e:
        log_action('文件下载失败', str(e))
        # 下载失败时拒绝文件
        reject_file(file_info['id'])
    finally:
        # 无论成功失败，清理临时文件
        file_id = file_info['id']
        file_path = file_info['path']
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                log_action('清理临时文件', f'{file_info["name"]}')
        except Exception as cleanup_error:
            log_action('清理临时文件失败', str(cleanup_error))
        
        # 从FILE_STATUS中移除记录
        if file_id in FILE_STATUS:
            del FILE_STATUS[file_id]

# 拒绝文件
def reject_file(file_id):
    if file_id in FILE_STATUS:
        file_info = FILE_STATUS[file_id]
        # 更新文件状态为已拒绝
        FILE_STATUS[file_id]['status'] = 'rejected'
        FILE_STATUS[file_id]['last_update'] = datetime.datetime.now().timestamp()
        
        # 发送状态更新通知
        send_file_status_update(file_id, 'rejected')
        
        # 清理临时文件
        file_path = file_info['path']
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                log_action('清理临时文件', f'{file_info["name"]}')
        except Exception as cleanup_error:
            log_action('清理临时文件失败', str(cleanup_error))
        
        # 记录日志
        log_action('文件被拒绝', file_info['name'])
        
        # 从FILE_STATUS中移除记录
        del FILE_STATUS[file_id]

# 发送文件状态更新通知
def send_file_status_update(file_id, status):
    if file_id in FILE_STATUS:
        file_info = FILE_STATUS[file_id]
        import json
        message = json.dumps({
            'type': 'file_status',
            'file_id': file_id,
            'file_name': file_info['name'],
            'status': status
        })
        send_to_all(message)



# SSE 路由
@app.route('/events')
def events():
    def generate():
        # 创建一个新的客户端
        client = SSEClient()
        clients.append(client)
        
        try:
            # 发送初始连接消息
            yield 'data: connected\n\n'
            
            # 无限循环，直到连接断开
            while True:
                # 检查是否有消息
                if client.has_message():
                    # 获取消息
                    message = client.get()
                    # 发送消息
                    yield f'data: {message}\n\n'
                # 等待100毫秒
                import time
                time.sleep(0.1)
        except GeneratorExit:
            # 连接断开，移除客户端
            if client in clients:
                clients.remove(client)
    
    # 返回 SSE 响应
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    return response

if __name__ == '__main__':
    # 检查是否以管理员权限运行
    if not is_admin():
        # 不是管理员权限，请求提升
        print('需要管理员权限才能正常运行文件管理功能')
        print('正在请求管理员权限提升...')
        if run_as_admin():
            # 成功请求提升，退出当前进程
            import sys
            sys.exit(0)
        else:
            # 提升失败，继续运行但可能有限制
            print('权限提升失败，文件管理功能可能受限')
    
    # 启动清理任务
    start_cleanup_task()
    
    log_action('服务器启动')
    app.run(host='0.0.0.0', port=5002, debug=False, threaded=True)