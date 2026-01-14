#!/bin/bash
# AI Quant Company - 本地启动脚本
# 用法: ./scripts/start_local.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   AI Quant Company - 本地启动${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 检查 Python 虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  未找到虚拟环境，正在创建...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate
echo -e "${GREEN}✅ Python 虚拟环境已激活${NC}"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ 未找到 .env 文件${NC}"
    echo -e "${YELLOW}请复制 env.example 并配置 API 密钥:${NC}"
    echo "cp env.example .env"
    exit 1
fi
echo -e "${GREEN}✅ .env 文件已找到${NC}"

# 安装依赖
echo ""
echo -e "${BLUE}📦 检查 Python 依赖...${NC}"
pip install -q -r requirements.txt 2>/dev/null || echo "依赖已安装"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ 未找到 Node.js，请先安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Node.js $(node --version) 已安装${NC}"

# 停止可能运行的旧进程
echo ""
echo -e "${BLUE}🛑 清理旧进程...${NC}"
pkill -f "uvicorn dashboard.api.main" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 2

# 启动后端
echo ""
echo -e "${BLUE}🚀 启动后端 API (端口 8000)...${NC}"
python -m uvicorn dashboard.api.main:app --host 0.0.0.0 --port 8000 > /tmp/aiquant_backend.log 2>&1 &
BACKEND_PID=$!
sleep 3

# 检查后端是否启动成功
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 后端 API 启动成功 (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}❌ 后端启动失败，查看日志: /tmp/aiquant_backend.log${NC}"
    cat /tmp/aiquant_backend.log | tail -20
    exit 1
fi

# 启动前端
echo ""
echo -e "${BLUE}🚀 启动前端 (端口 3000)...${NC}"
cd dashboard/web

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠️  未找到 node_modules，正在安装依赖...${NC}"
    npm install
fi

npm run dev > /tmp/aiquant_frontend.log 2>&1 &
FRONTEND_PID=$!
cd "$PROJECT_ROOT"
sleep 5

# 检查前端是否启动成功
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 前端启动成功 (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${YELLOW}⚠️  前端可能仍在编译中...${NC}"
fi

# 显示启动信息
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   🎉 AI Quant Company 已启动!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "📊 仪表盘:    ${BLUE}http://localhost:3000${NC}"
echo -e "🔧 API 文档:  ${BLUE}http://localhost:8000/docs${NC}"
echo -e "💓 健康检查:  ${BLUE}http://localhost:8000/health${NC}"
echo ""
echo -e "📝 日志文件:"
echo -e "   后端: /tmp/aiquant_backend.log"
echo -e "   前端: /tmp/aiquant_frontend.log"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo ""

# 保存 PID
echo $BACKEND_PID > /tmp/aiquant_backend.pid
echo $FRONTEND_PID > /tmp/aiquant_frontend.pid

# 等待退出信号
trap "echo '停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# 持续运行
while true; do
    sleep 60
    # 检查进程是否存活
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${RED}❌ 后端进程已退出${NC}"
        break
    fi
done
