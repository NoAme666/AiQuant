#!/bin/bash
# =============================================================
# AI Quant Company - 数据库部署脚本 (手动执行版)
# =============================================================
# 
# 使用方法:
#   1. 通过 SSH 或控制台登录到服务器
#   2. 将此脚本内容复制粘贴到服务器
#   3. 运行: bash deploy_database_manual.sh
#
# 或者直接复制下面的命令逐步执行
# =============================================================

set -e

echo "============================================"
echo "AI Quant Company - PostgreSQL + pgvector 部署"
echo "============================================"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 配置
DB_NAME="aiquant"
DB_USER="aiquant"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -base64 24 | tr -d '+/=' | head -c 20)}"
PG_VERSION="16"

# =============================================================
# Step 1: 检测操作系统
# =============================================================
log_info "检测操作系统..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
    log_info "检测到: $OS $VERSION"
else
    log_error "无法检测操作系统"
    exit 1
fi

# =============================================================
# Step 2: 安装 PostgreSQL 16
# =============================================================
log_info "安装 PostgreSQL $PG_VERSION..."

if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    # 添加 PostgreSQL 官方仓库
    apt-get update
    apt-get install -y wget gnupg2 lsb-release curl ca-certificates
    
    # 添加 PostgreSQL APT 仓库
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
    echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
    
    apt-get update
    apt-get install -y postgresql-$PG_VERSION postgresql-contrib-$PG_VERSION postgresql-server-dev-$PG_VERSION build-essential git
    
elif [ "$OS" == "centos" ] || [ "$OS" == "rhel" ] || [ "$OS" == "rocky" ] || [ "$OS" == "almalinux" ]; then
    # 安装 PostgreSQL 仓库
    yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-${VERSION%%.*}-x86_64/pgdg-redhat-repo-latest.noarch.rpm
    yum install -y postgresql$PG_VERSION-server postgresql$PG_VERSION-contrib postgresql$PG_VERSION-devel gcc git make
    
    # 初始化数据库
    /usr/pgsql-$PG_VERSION/bin/postgresql-$PG_VERSION-setup initdb
    
else
    log_error "不支持的操作系统: $OS"
    exit 1
fi

log_info "PostgreSQL $PG_VERSION 安装完成"

# =============================================================
# Step 3: 安装 pgvector
# =============================================================
log_info "安装 pgvector 扩展..."

cd /tmp
if [ -d "pgvector" ]; then
    rm -rf pgvector
fi

git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git
cd pgvector

if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    make PG_CONFIG=/usr/lib/postgresql/$PG_VERSION/bin/pg_config
    make PG_CONFIG=/usr/lib/postgresql/$PG_VERSION/bin/pg_config install
else
    make PG_CONFIG=/usr/pgsql-$PG_VERSION/bin/pg_config
    make PG_CONFIG=/usr/pgsql-$PG_VERSION/bin/pg_config install
fi

cd /tmp
rm -rf pgvector

log_info "pgvector 安装完成"

# =============================================================
# Step 4: 配置 PostgreSQL
# =============================================================
log_info "配置 PostgreSQL..."

if [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
    PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
    PG_SERVICE="postgresql"
else
    PG_CONF="/var/lib/pgsql/$PG_VERSION/data/postgresql.conf"
    PG_HBA="/var/lib/pgsql/$PG_VERSION/data/pg_hba.conf"
    PG_SERVICE="postgresql-$PG_VERSION"
fi

# 监听所有接口
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" $PG_CONF
sed -i "s/listen_addresses = 'localhost'/listen_addresses = '*'/" $PG_CONF

# 允许远程连接（只允许 aiquant 用户访问 aiquant 数据库）
if ! grep -q "host.*aiquant.*aiquant.*0.0.0.0/0" $PG_HBA; then
    echo "# AI Quant Company remote access" >> $PG_HBA
    echo "host    aiquant    aiquant    0.0.0.0/0    scram-sha-256" >> $PG_HBA
fi

# 启动/重启 PostgreSQL
systemctl enable $PG_SERVICE
systemctl restart $PG_SERVICE

log_info "PostgreSQL 配置完成"

# =============================================================
# Step 5: 创建数据库和用户
# =============================================================
log_info "创建数据库和用户..."

sudo -u postgres psql -v ON_ERROR_STOP=1 <<EOF
-- 创建用户（如果不存在）
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    ELSE
        ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    END IF;
END
\$\$;

-- 创建数据库（如果不存在）
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER' 
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- 连接到数据库并创建扩展
\c $DB_NAME

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
GRANT ALL PRIVILEGES ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO $DB_USER;

\q
EOF

log_info "数据库和用户创建完成"

# =============================================================
# Step 6: 配置防火墙
# =============================================================
log_info "配置防火墙..."

if command -v ufw &> /dev/null; then
    ufw allow 5432/tcp
    log_info "UFW: 已开放 5432 端口"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=5432/tcp
    firewall-cmd --reload
    log_info "Firewalld: 已开放 5432 端口"
else
    log_warn "未检测到防火墙工具，请手动确保 5432 端口开放"
fi

# =============================================================
# Step 7: 验证安装
# =============================================================
log_info "验证安装..."

# 测试连接
PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME -c "SELECT 1 as test;" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    log_info "✅ 数据库连接测试成功"
else
    log_error "数据库连接测试失败"
fi

# 测试 pgvector
PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME -c "SELECT '[1,2,3]'::vector;" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    log_info "✅ pgvector 扩展测试成功"
else
    log_error "pgvector 扩展测试失败"
fi

# =============================================================
# 完成
# =============================================================
echo ""
echo "============================================"
echo "        部署完成！"
echo "============================================"
echo ""
echo "数据库连接信息:"
echo "  Host:     $(hostname -I | awk '{print $1}')"
echo "  Port:     5432"
echo "  Database: $DB_NAME"
echo "  User:     $DB_USER"
echo "  Password: $DB_PASSWORD"
echo ""
echo "连接字符串 (DATABASE_URL):"
echo "  postgresql+asyncpg://$DB_USER:$DB_PASSWORD@$(hostname -I | awk '{print $1}'):5432/$DB_NAME"
echo ""
echo "下一步:"
echo "  1. 保存上述密码到安全位置"
echo "  2. 将 schema.sql 文件传输到服务器"
echo "  3. 运行: PGPASSWORD='$DB_PASSWORD' psql -h localhost -U $DB_USER -d $DB_NAME -f schema.sql"
echo ""
echo "============================================"
