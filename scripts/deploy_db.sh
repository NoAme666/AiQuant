#!/bin/bash
# AI Quant Company - PostgreSQL + pgvector 部署脚本
# 目标服务器: 154.26.181.47
# 
# 使用方法:
#   ssh root@154.26.181.47 'bash -s' < scripts/deploy_db.sh
#   或者直接在服务器上运行

set -e

echo "============================================"
echo "AI Quant - PostgreSQL + pgvector 部署"
echo "============================================"

# 配置变量
DB_NAME="aiquant"
DB_USER="aiquant"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 32)}"
PG_VERSION="16"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 检测操作系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        log_warn "无法检测操作系统"
        OS="unknown"
    fi
    log_info "检测到操作系统: $OS $VERSION"
}

# 安装 PostgreSQL (Ubuntu/Debian)
install_postgresql_debian() {
    log_info "安装 PostgreSQL $PG_VERSION..."
    
    # 添加 PostgreSQL APT 仓库
    apt-get update
    apt-get install -y wget gnupg2 lsb-release
    
    # 添加 PostgreSQL 官方仓库
    sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
    
    apt-get update
    apt-get install -y postgresql-$PG_VERSION postgresql-contrib-$PG_VERSION
    
    # 安装 pgvector 编译依赖
    apt-get install -y build-essential git postgresql-server-dev-$PG_VERSION
}

# 安装 pgvector
install_pgvector() {
    log_info "安装 pgvector 扩展..."
    
    cd /tmp
    if [ -d "pgvector" ]; then
        rm -rf pgvector
    fi
    
    git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git
    cd pgvector
    make
    make install
    
    log_info "pgvector 安装完成"
}

# 配置 PostgreSQL
configure_postgresql() {
    log_info "配置 PostgreSQL..."
    
    PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
    PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    
    # 配置监听地址
    sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" $PG_CONF
    
    # 配置内存参数 (根据服务器内存调整)
    sed -i "s/shared_buffers = 128MB/shared_buffers = 256MB/" $PG_CONF
    sed -i "s/#work_mem = 4MB/work_mem = 64MB/" $PG_CONF
    sed -i "s/#maintenance_work_mem = 64MB/maintenance_work_mem = 256MB/" $PG_CONF
    
    # 配置远程访问
    echo "" >> $PG_HBA
    echo "# AI Quant 远程访问" >> $PG_HBA
    echo "host    $DB_NAME    $DB_USER    0.0.0.0/0    scram-sha-256" >> $PG_HBA
    
    # 重启 PostgreSQL
    systemctl restart postgresql
    
    log_info "PostgreSQL 配置完成"
}

# 创建数据库和用户
create_database() {
    log_info "创建数据库和用户..."
    
    # 切换到 postgres 用户执行
    sudo -u postgres psql <<EOF
-- 创建用户
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- 创建数据库
CREATE DATABASE $DB_NAME OWNER $DB_USER;

-- 授权
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- 连接到数据库并创建扩展
\c $DB_NAME

-- 创建扩展 (需要 superuser)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 授予 schema 权限
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO $DB_USER;
EOF

    log_info "数据库和用户创建完成"
}

# 初始化 schema
init_schema() {
    log_info "初始化数据库 Schema..."
    
    # 如果有 schema.sql 文件，执行它
    if [ -f "/tmp/schema.sql" ]; then
        sudo -u postgres psql -d $DB_NAME -f /tmp/schema.sql
        log_info "Schema 初始化完成"
    else
        log_warn "schema.sql 文件不存在，跳过 Schema 初始化"
        log_warn "请手动执行: psql -h localhost -U $DB_USER -d $DB_NAME -f storage/schema.sql"
    fi
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."
    
    if command -v ufw &> /dev/null; then
        ufw allow 5432/tcp
        log_info "UFW 防火墙已配置"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=5432/tcp
        firewall-cmd --reload
        log_info "Firewalld 防火墙已配置"
    else
        log_warn "未检测到防火墙，请手动开放 5432 端口"
    fi
}

# 打印连接信息
print_connection_info() {
    echo ""
    echo "============================================"
    echo "PostgreSQL 部署完成!"
    echo "============================================"
    echo ""
    echo "连接信息:"
    echo "  Host: 154.26.181.47"
    echo "  Port: 5432"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo "  Password: $DB_PASSWORD"
    echo ""
    echo "连接字符串:"
    echo "  postgresql://$DB_USER:$DB_PASSWORD@154.26.181.47:5432/$DB_NAME"
    echo ""
    echo "AsyncPG 连接字符串 (用于 .env):"
    echo "  DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@154.26.181.47:5432/$DB_NAME"
    echo ""
    echo "测试连接:"
    echo "  psql -h 154.26.181.47 -U $DB_USER -d $DB_NAME"
    echo ""
    echo "============================================"
    echo "重要: 请保存以上密码并更新 .env 文件!"
    echo "============================================"
}

# 主函数
main() {
    detect_os
    
    case $OS in
        ubuntu|debian)
            install_postgresql_debian
            ;;
        *)
            log_warn "不支持的操作系统: $OS"
            log_warn "请手动安装 PostgreSQL $PG_VERSION 和 pgvector"
            exit 1
            ;;
    esac
    
    install_pgvector
    configure_postgresql
    create_database
    init_schema
    configure_firewall
    print_connection_info
}

# 运行
main "$@"
