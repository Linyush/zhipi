#!/bin/bash

# 切换到项目根目录
cd "$(dirname "$0")/.."

echo "========================================"
echo "  智批 - 停止脚本"
echo "========================================"
echo ""

PORT=8000
if [ -f ".env" ]; then
    ENV_PORT=$(grep -E '^SERVER_PORT=' .env | tail -n1 | cut -d= -f2)
    if [ -n "$ENV_PORT" ]; then
        PORT="$ENV_PORT"
    fi
fi

# 从 PID 文件读取进程 ID
if [ -f ".server.pid" ]; then
    PID=$(cat .server.pid)
    echo "正在停止服务 (PID: $PID)..."
    
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        
        # 等待进程结束
        for i in {1..5}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # 如果还在运行，强制终止
        if ps -p $PID > /dev/null 2>&1; then
            echo "进程未响应，强制终止..."
            kill -9 $PID
        fi
        
        echo "服务已停止"
    else
        echo "[警告] 进程不存在"
    fi
    
    rm -f .server.pid
else
    echo "[警告] 未找到 PID 文件"
    echo "尝试通过端口查找进程..."
    
    # 通过端口查找进程
    PID=$(lsof -ti:$PORT)
    if [ ! -z "$PID" ]; then
        echo "找到占用 $PORT 端口的进程: $PID"
        kill $PID
        sleep 1
        
        # 检查是否还在运行
        if lsof -ti:$PORT > /dev/null 2>&1; then
            echo "强制终止进程..."
            kill -9 $PID
        fi
        echo "服务已停止"
    else
        echo "未找到运行中的服务"
    fi
fi

echo ""
echo "========================================"
echo "  服务已停止"
echo "========================================"
echo ""
