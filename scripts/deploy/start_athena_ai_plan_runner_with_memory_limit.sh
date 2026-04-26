#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
PID_FILE="$ROOT/.openclaw/athena_ai_plan_runner.pid"
SESSION_NAME="athena_plan_runner"
MEMORY_LIMIT_MB=8192  # 8GB内存限制，根据M4的16GB内存调整

mkdir -p "$ROOT/.openclaw" "$ROOT/logs"

# Check if PID file exists and process is alive
if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE" 2>/dev/null | tr -d '\n')
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "$PID"
    exit 0
  else
    # Stale PID file
    rm -f "$PID_FILE"
  fi
fi

# Check for existing screen session
SCREEN_PID="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { split($1, parts, "."); print parts[1]; exit }')"
if [[ -n "${SCREEN_PID:-}" ]]; then
  echo "${SCREEN_PID:-Athena AI plan runner already running in screen}"
  exit 0
fi

# Check for existing process via pgrep (fallback)
EXISTING_PID="$(pgrep -f "$ROOT/scripts/athena_ai_plan_runner.py" | head -n 1 || true)"
if [[ -n "${EXISTING_PID:-}" ]]; then
  echo "${EXISTING_PID:-Athena AI plan runner already running}"
  exit 0
fi

# Create a wrapper script with memory monitoring
MEMORY_WRAPPER_SCRIPT="$ROOT/scripts/memory_monitored_runner.py"

cat > "$MEMORY_WRAPPER_SCRIPT" << 'EOF'
#!/usr/bin/env python3
"""
内存监控的队列运行器包装脚本
监控Python进程内存使用，超过限制时重启
"""

import os
import sys
import time
import signal
import psutil
import subprocess
from threading import Thread
from datetime import datetime

# 内存限制（MB）
MEMORY_LIMIT_MB = 8192  # 8GB
CHECK_INTERVAL = 300  # 每5分钟检查一次（秒）
LOG_FILE = "/Volumes/1TB-M2/openclaw/logs/memory_monitor.log"

def log_message(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)

    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    except:
        pass

def monitor_memory(pid):
    """监控进程内存使用"""
    log_message(f"开始监控进程 {pid} 的内存使用")

    while True:
        try:
            process = psutil.Process(pid)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # 转换为MB

            log_message(f"进程 {pid} 内存使用: {memory_mb:.2f} MB / {MEMORY_LIMIT_MB} MB")

            # 检查是否超过限制
            if memory_mb > MEMORY_LIMIT_MB:
                log_message(f"⚠️  进程 {pid} 内存使用超过限制 ({memory_mb:.2f} MB > {MEMORY_LIMIT_MB} MB)")
                log_message(f"🔄 发送SIGTERM信号终止进程")

                # 先尝试优雅终止
                process.terminate()
                time.sleep(5)

                # 如果还在运行，强制终止
                if process.is_running():
                    process.kill()
                    log_message(f"🔫 强制终止进程 {pid}")

                return False  # 监控停止

        except psutil.NoSuchProcess:
            log_message(f"进程 {pid} 已退出")
            return True  # 正常退出
        except Exception as e:
            log_message(f"监控错误: {e}")

        time.sleep(CHECK_INTERVAL)

def main():
    """主函数"""
    log_message("=" * 60)
    log_message("启动内存监控的队列运行器")
    log_message(f"内存限制: {MEMORY_LIMIT_MB} MB")
    log_message("=" * 60)

    # 启动实际的队列运行器
    runner_script = "/Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py"

    if not os.path.exists(runner_script):
        log_message(f"❌ 队列运行器脚本不存在: {runner_script}")
        return 1

    # 启动子进程
    log_message(f"启动队列运行器: {runner_script}")

    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'  # 确保实时输出

    try:
        process = subprocess.Popen(
            [sys.executable, runner_script],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        log_message(f"队列运行器进程ID: {process.pid}")

        # 启动内存监控线程
        monitor_thread = Thread(target=monitor_memory, args=(process.pid,))
        monitor_thread.daemon = True
        monitor_thread.start()

        # 读取输出
        for line in iter(process.stdout.readline, ''):
            print(line.rstrip())

        # 等待进程结束
        return_code = process.wait()
        log_message(f"队列运行器退出，返回码: {return_code}")

        monitor_thread.join(timeout=10)

        return return_code

    except KeyboardInterrupt:
        log_message("收到中断信号，终止进程")
        if 'process' in locals() and process.poll() is None:
            process.terminate()
            process.wait()
        return 0
    except Exception as e:
        log_message(f"启动队列运行器失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

# 使包装脚本可执行
chmod +x "$MEMORY_WRAPPER_SCRIPT"

# 安装psutil（如果未安装）
if ! python3 -c "import psutil" 2>/dev/null; then
    echo "安装psutil用于内存监控..."
    pip3 install psutil
fi

# 启动带内存监控的screen会话
echo "启动带内存监控的Athena AI plan runner (内存限制: ${MEMORY_LIMIT_MB}MB)..."
screen -dmS "$SESSION_NAME" env DASHSCOPE_API_KEY="$DASHSCOPE_API_KEY" /opt/homebrew/bin/python3 "$MEMORY_WRAPPER_SCRIPT"

sleep 2
SCREEN_PID="$( { screen -ls 2>/dev/null || true; } | awk '/[.]'"${SESSION_NAME}"'[[:space:]]/ { split($1, parts, "."); print parts[1]; exit }')"

if [[ -n "${SCREEN_PID:-}" ]]; then
    echo "✅ Athena AI plan runner已启动 (带内存监控)"
    echo "   Screen会话PID: ${SCREEN_PID}"
    echo "   内存限制: ${MEMORY_LIMIT_MB} MB"
    echo "   日志文件: /Volumes/1TB-M2/openclaw/logs/memory_monitor.log"
    echo ""
    echo "查看状态: screen -r ${SESSION_NAME}"
    echo "查看内存日志: tail -f /Volumes/1TB-M2/openclaw/logs/memory_monitor.log"

    # 保存PID
    echo "${SCREEN_PID}" > "$PID_FILE"
else
    echo "❌ 启动失败，请检查日志"
    exit 1
fi