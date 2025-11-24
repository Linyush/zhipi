#!/bin/bash

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 解析命令行参数
DEBUG_MODE=false
if [ "$1" == "--debug" ]; then
    DEBUG_MODE=true
fi

echo "========================================"
if [ "$DEBUG_MODE" = true ]; then
    echo "  智批 - 启动脚本 (调试模式)"
else
    echo "  智批 - 启动脚本"
fi
echo "========================================"
echo ""

# ==================== 环境检查 ====================

echo "[1/5] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python3"
    echo ""
    echo "请安装 Python 3.8 或更高版本："
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macOS 系统，推荐使用 Homebrew 安装："
        echo "  brew install python3"
        echo ""
        echo "或从官网下载: https://www.python.org/downloads/"
    else
        echo "Linux 系统，使用包管理器安装："
        echo "  sudo apt-get install python3 python3-pip  # Ubuntu/Debian"
        echo "  sudo yum install python3 python3-pip      # CentOS/RHEL"
    fi
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本: $PYTHON_VERSION"

# 检查虚拟环境
echo ""
echo "[2/5] 检查虚拟环境..."
if [ ! -d "venv" ]; then
    echo "虚拟环境不存在，正在创建..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[错误] 创建虚拟环境失败"
        exit 1
    fi
    echo "虚拟环境创建成功"
else
    echo "虚拟环境已存在"
fi

# 激活虚拟环境
echo ""
echo "[3/5] 激活虚拟环境..."
source venv/bin/activate

# 检查并安装依赖
echo ""
echo "[4/5] 检查依赖包..."
if ! python -c "import fastapi" &> /dev/null; then
    echo "依赖包未安装，正在安装..."
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if [ $? -ne 0 ]; then
        echo "[警告] 依赖包安装失败，尝试使用默认源..."
        pip install -r requirements.txt
    fi
else
    echo "依赖包已安装"
fi

# 检查配置文件
echo ""
echo "[5/5] 检查配置文件..."
if [ ! -f ".env" ]; then
    echo "[警告] 未找到 .env 配置文件"
    if [ -f ".env.example" ]; then
        echo "正在从 .env.example 创建 .env..."
        cp .env.example .env
        echo ""
        echo "[重要] 请编辑 .env 文件，填入你的 API 密钥"
        echo "文件位置: $(pwd)/.env"
        echo ""
        echo "按回车键打开编辑器..."
        read
        ${EDITOR:-nano} .env
        echo ""
        echo "配置完成后，请重新运行此脚本"
        exit 0
    else
        echo "[错误] 未找到 .env.example 文件"
        exit 1
    fi
else
    echo "配置文件已存在"
fi

# ==================== 启动服务 ====================

echo ""
echo "========================================"
echo "  正在启动服务..."
echo "========================================"
echo ""

# 检查是否已有进程在运行（仅在非调试模式下检查）
if [ "$DEBUG_MODE" = false ]; then
    if [ -f ".server.pid" ]; then
        PID=$(cat .server.pid)
        if ps -p $PID > /dev/null 2>&1; then
            echo "[警告] 服务可能已在运行 (PID: $PID)"
            echo "如需重启，请先运行: ./scripts/stop.sh"
            echo ""
            exit 0
        else
            # PID 文件存在但进程不存在，清理
            rm -f .server.pid
        fi
    fi
fi

# 创建日志目录
mkdir -p logs

if [ "$DEBUG_MODE" = true ]; then
    # 调试模式：前台运行
    echo "启动服务 (前台运行，按 Ctrl+C 停止)..."
    echo ""
    echo "========================================"
    echo ""

    # 自动打开浏览器
    sleep 2 && {
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open http://localhost:8000/static/pc.html
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command -v xdg-open &> /dev/null; then
                xdg-open http://localhost:8000/static/pc.html
            elif command -v gnome-open &> /dev/null; then
                gnome-open http://localhost:8000/static/pc.html
            fi
        fi
    } &

    # 前台运行，日志直接输出到终端
    python main.py
else
    # 后台模式：后台运行
    echo "启动后台服务..."
    nohup python main.py > logs/server.log 2>&1 &
    SERVER_PID=$!
    echo $SERVER_PID > .server.pid

    # 等待服务启动
    echo "等待服务启动..."
    sleep 3

    # 检查服务是否成功启动
    if ! curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "[错误] 服务启动失败，请查看日志: logs/server.log"
        rm -f .server.pid
        exit 1
    fi

    echo ""
    echo "========================================"
    echo "  服务启动成功！"
    echo "========================================"
    echo "  PID: $SERVER_PID"
    echo "  访问地址: http://localhost:8000/static/pc.html"
    echo "  API 文档: http://localhost:8000/docs"
    echo "  日志文件: logs/server.log"
    echo ""
    echo "  使用 ./scripts/stop.sh 停止服务"
    echo "========================================"
    echo ""

    # 自动打开浏览器
    echo "正在打开浏览器..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open http://localhost:8000/static/pc.html
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v xdg-open &> /dev/null; then
            xdg-open http://localhost:8000/static/pc.html
        elif command -v gnome-open &> /dev/null; then
            gnome-open http://localhost:8000/static/pc.html
        fi
    fi

    echo ""
    echo "服务已在后台运行"
    echo ""
fi
