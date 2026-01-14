#!/bin/bash
# AI Quant Company - 停止本地服务脚本
# 用法: ./scripts/stop_local.sh

echo "🛑 停止 AI Quant Company 服务..."

# 停止后端
if [ -f /tmp/aiquant_backend.pid ]; then
    kill $(cat /tmp/aiquant_backend.pid) 2>/dev/null && echo "✅ 后端已停止"
    rm /tmp/aiquant_backend.pid
fi
pkill -f "uvicorn dashboard.api.main" 2>/dev/null

# 停止前端
if [ -f /tmp/aiquant_frontend.pid ]; then
    kill $(cat /tmp/aiquant_frontend.pid) 2>/dev/null && echo "✅ 前端已停止"
    rm /tmp/aiquant_frontend.pid
fi
pkill -f "next dev" 2>/dev/null

echo "✅ 所有服务已停止"
