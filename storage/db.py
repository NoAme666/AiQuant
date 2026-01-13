# AI Quant Company - 数据库连接与会话管理
"""
数据库连接模块

提供:
- 异步数据库连接池
- 会话管理
- 事务支持
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

# ============================================
# 配置
# ============================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/aiquant"
)

# 连接池配置
POOL_SIZE = int(os.getenv("DATABASE_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))

# ============================================
# 引擎与会话
# ============================================

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_pre_ping=True,  # 检查连接有效性
)

# 测试环境使用 NullPool（不池化）
test_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

# 会话工厂
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ============================================
# 基类
# ============================================

class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass

# ============================================
# 会话管理
# ============================================

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的上下文管理器
    
    使用方法:
        async with get_session() as session:
            result = await session.execute(query)
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入用的会话获取器
    
    使用方法:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session_dependency)):
            ...
    """
    async with get_session() as session:
        yield session


# ============================================
# 生命周期管理
# ============================================

async def init_db() -> None:
    """初始化数据库（创建表）
    
    注意：生产环境应使用 Alembic 迁移
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接池"""
    await engine.dispose()


# ============================================
# 健康检查
# ============================================

async def check_db_health() -> bool:
    """检查数据库连接健康状态"""
    try:
        async with get_session() as session:
            await session.execute("SELECT 1")
        return True
    except Exception:
        return False


# ============================================
# 事务辅助
# ============================================

@asynccontextmanager
async def transaction():
    """事务上下文管理器（带自动回滚）
    
    使用方法:
        async with transaction() as session:
            session.add(obj1)
            session.add(obj2)
            # 自动提交或回滚
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
