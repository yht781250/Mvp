"""
数据库连接与会话管理

采用 SQLite 零运维方案，适合单用户本地部署场景。
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.settings import settings


# 确保 data 目录存在
data_dir = Path(settings.sqlite_path).parent
data_dir.mkdir(parents=True, exist_ok=True)

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite 专用参数
    echo=False,  # 生产环境关闭 SQL 日志
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明式基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入用：获取数据库会话

    用法:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    上下文管理器：用于非 FastAPI 场景

    用法:
        with get_db_context() as db:
            db.query(Fund).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    初始化数据库：创建所有表

    在应用启动或首次使用时调用。
    """
    # 导入 models 以确保表被注册到 Base.metadata
    from app.data import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
