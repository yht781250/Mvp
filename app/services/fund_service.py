"""
基金服务层

提供基金信息的增删改查操作。
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.models import Fund, FundType


def get_fund_by_code(db: Session, code: str) -> Optional[Fund]:
    """根据基金代码查询基金"""
    stmt = select(Fund).where(Fund.code == code)
    return db.execute(stmt).scalar_one_or_none()


def get_fund_by_id(db: Session, fund_id: int) -> Optional[Fund]:
    """根据ID查询基金"""
    return db.get(Fund, fund_id)


def get_all_funds(db: Session) -> list[Fund]:
    """获取所有基金"""
    stmt = select(Fund).order_by(Fund.code)
    return list(db.execute(stmt).scalars().all())


def create_fund(
    db: Session,
    code: str,
    name: str,
    fund_type: FundType = FundType.OTHER,
    **kwargs,
) -> Fund:
    """
    创建基金记录

    如果基金已存在则返回已有记录。
    """
    existing = get_fund_by_code(db, code)
    if existing:
        return existing

    fund = Fund(code=code, name=name, fund_type=fund_type, **kwargs)
    db.add(fund)
    db.flush()
    return fund


def get_or_create_fund(
    db: Session,
    code: str,
    name: str,
    fund_type: FundType = FundType.OTHER,
) -> tuple[Fund, bool]:
    """
    获取或创建基金

    如果基金已存在但名称不同，会更新名称。

    返回: (基金对象, 是否新创建)
    """
    existing = get_fund_by_code(db, code)
    if existing:
        # 如果名称不同，更新为新名称
        if existing.name != name:
            existing.name = name
            db.flush()
        return existing, False

    fund = Fund(code=code, name=name, fund_type=fund_type)
    db.add(fund)
    db.flush()
    return fund, True
