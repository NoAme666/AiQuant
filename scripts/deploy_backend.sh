#!/bin/bash
# AI Quant Company - FastAPI 后端部署脚本
# 目标服务器: 154.26.181.47
#
# 使用方法:
#   1. 先部署数据库: ssh root@154.26.181.47 'bash -s' < scripts/deploy_db.sh
#   2. 同步代码到服务器: rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '.venv' ./ root@154.26.181.47:/opt/aiquant/
#   3. 运行此脚本: ssh root@154.26.181.47 'bash /opt/aiquant/scripts/deploy_backend.sh'

set -e

echo "============================================"
echo "AI Quant - FastAPI 后端部署"
echo "============================================"

# 配置变量
APP_DIR="/opt/aiquant"
APP_USER="aiquant"
PYTHON_VERSION="3.11"
SERVICE_NAME="aiquant"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 创建应用用户
create_app_user() {
    log_info "创建应用用户..."
    
    if id "$APP_USER" &>/dev/null; then
        log_info "用户 $APP_USER 已存在"
    else
        useradd -r -s /bin/false -d $APP_DIR $APP_USER
        log_info "用户 $APP_USER 创建完成"
    fi
}

# 安装 Python
install_python() {
    log_info "安装 Python $PYTHON_VERSION..."
    
    apt-get update
    apt-get install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    apt-get install -y python$PYTHON_VERSION python$PYTHON_VERSION-venv python$PYTHON_VERSION-dev
    
    log_info "Python $PYTHON_VERSION 安装完成"
}

# 设置应用目录
setup_app_directory() {
    log_info "设置应用目录..."
    
    mkdir -p $APP_DIR
    mkdir -p $APP_DIR/logs
    mkdir -p $APP_DIR/artifacts
    mkdir -p $APP_DIR/data/parquet
    mkdir -p $APP_DIR/reports/output
    
    # 设置权限
    chown -R $APP_USER:$APP_USER $APP_DIR
    
    log_info "应用目录设置完成"
}

# 创建虚拟环境并安装依赖
setup_virtualenv() {
    log_info "创建虚拟环境..."
    
    cd $APP_DIR
    
    # 创建虚拟环境
    python$PYTHON_VERSION -m venv venv
    
    # 激活并安装依赖
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_info "虚拟环境设置完成"
}

# 创建环境文件
create_env_file() {
    log_info "创建环境文件..."
    
    if [ ! -f "$APP_DIR/.env" ]; then
        if [ -f "$APP_DIR/env.example" ]; then
            cp $APP_DIR/env.example $APP_DIR/.env
            log_warn "已从 env.example 创建 .env，请编辑并填入实际值"
        else
            cat > $APP_DIR/.env <<EOF
# AI Quant Company - 生产环境配置

# 数据库
DATABASE_URL=postgresql+asyncpg://aiquant:YOUR_PASSWORD@localhost:5432/aiquant

# Antigravity AI Service
ANTIGRAVITY_API_KEY=your-antigravity-api-key
ANTIGRAVITY_BASE_URL=https://your-antigravity-endpoint.com/v1
EMBEDDING_MODEL=text-embedding-3-small

# 应用配置
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# 服务
API_HOST=0.0.0.0
API_PORT=8000

# 安全
SECRET_KEY=$(openssl rand -base64 32)

# CORS
CORS_ORIGINS=https://aiquant.vercel.app,https://*.vercel.app

# 存储
ARTIFACTS_PATH=$APP_DIR/artifacts
PARQUET_PATH=$APP_DIR/data/parquet
REPORTS_PATH=$APP_DIR/reports/output
EOF
            log_warn "已创建默认 .env 文件，请编辑并填入实际值"
        fi
    else
        log_info ".env 文件已存在"
    fi
    
    # 设置权限
    chmod 600 $APP_DIR/.env
    chown $APP_USER:$APP_USER $APP_DIR/.env
}

# 创建 systemd 服务
create_systemd_service() {
    log_info "创建 systemd 服务..."
    
    cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=AI Quant FastAPI Backend
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/uvicorn dashboard.api.main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=append:$APP_DIR/logs/stdout.log
StandardError=append:$APP_DIR/logs/stderr.log

# 安全配置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR

[Install]
WantedBy=multi-user.target
EOF

    # 重载 systemd
    systemctl daemon-reload
    
    log_info "systemd 服务创建完成"
}

# 配置 logrotate
configure_logrotate() {
    log_info "配置日志轮转..."
    
    cat > /etc/logrotate.d/$SERVICE_NAME <<EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 $APP_USER $APP_USER
    sharedscripts
    postrotate
        systemctl reload $SERVICE_NAME > /dev/null 2>&1 || true
    endscript
}
EOF

    log_info "日志轮转配置完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."
    
    if command -v ufw &> /dev/null; then
        ufw allow 8000/tcp
        log_info "UFW 防火墙已配置"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=8000/tcp
        firewall-cmd --reload
        log_info "Firewalld 防火墙已配置"
    else
        log_warn "未检测到防火墙，请手动开放 8000 端口"
    fi
}

# 启动服务
start_service() {
    log_info "启动服务..."
    
    systemctl enable $SERVICE_NAME
    systemctl start $SERVICE_NAME
    
    # 等待启动
    sleep 3
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        log_info "服务启动成功"
    else
        log_warn "服务启动失败，请检查日志: journalctl -u $SERVICE_NAME -f"
    fi
}

# 打印部署信息
print_deployment_info() {
    echo ""
    echo "============================================"
    echo "FastAPI 后端部署完成!"
    echo "============================================"
    echo ""
    echo "服务信息:"
    echo "  服务名: $SERVICE_NAME"
    echo "  目录: $APP_DIR"
    echo "  端口: 8000"
    echo ""
    echo "服务管理:"
    echo "  启动: systemctl start $SERVICE_NAME"
    echo "  停止: systemctl stop $SERVICE_NAME"
    echo "  重启: systemctl restart $SERVICE_NAME"
    echo "  状态: systemctl status $SERVICE_NAME"
    echo "  日志: journalctl -u $SERVICE_NAME -f"
    echo ""
    echo "API 地址:"
    echo "  http://154.26.181.47:8000"
    echo "  http://154.26.181.47:8000/docs (Swagger UI)"
    echo ""
    echo "============================================"
    echo "重要: 请编辑 $APP_DIR/.env 填入正确的配置!"
    echo "============================================"
}

# 主函数
main() {
    # 检查是否为 root
    if [ "$EUID" -ne 0 ]; then
        echo "请使用 root 用户运行此脚本"
        exit 1
    fi
    
    # 检查代码是否存在
    if [ ! -f "$APP_DIR/requirements.txt" ]; then
        echo "错误: 请先将代码同步到 $APP_DIR"
        echo "使用: rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '.venv' ./ root@154.26.181.47:$APP_DIR/"
        exit 1
    fi
    
    create_app_user
    install_python
    setup_app_directory
    setup_virtualenv
    create_env_file
    create_systemd_service
    configure_logrotate
    configure_firewall
    start_service
    print_deployment_info
}

# 运行
main "$@"
