"""
净值服务层

提供净值数据的存储、更新和查询功能。
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.data.models import Fund, NavHistory
from app.services.fund_data_fetcher import fetch_nav_history, NavRecord


def get_latest_nav(db: Session, fund_id: int) -> Optional[NavHistory]:
    """获取基金最新净值"""
    stmt = (
        select(NavHistory)
        .where(NavHistory.fund_id == fund_id)
        .order_by(NavHistory.nav_date.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_nav_history(
    db: Session,
    fund_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 30,
) -> list[NavHistory]:
    """获取基金历史净值"""
    stmt = select(NavHistory).where(NavHistory.fund_id == fund_id)

    if start_date:
        stmt = stmt.where(NavHistory.nav_date >= start_date)
    if end_date:
        stmt = stmt.where(NavHistory.nav_date <= end_date)

    stmt = stmt.order_by(NavHistory.nav_date.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def save_nav_record(
    db: Session,
    fund_id: int,
    nav_date: date,
    nav: Decimal,
    acc_nav: Optional[Decimal] = None,
    daily_return: Optional[Decimal] = None,
) -> NavHistory:
    """保存单条净值记录（存在则更新）"""
    stmt = select(NavHistory).where(
        and_(NavHistory.fund_id == fund_id, NavHistory.nav_date == nav_date)
    )
    existing = db.execute(stmt).scalar_one_or_none()

    if existing:
        existing.nav = nav
        if acc_nav is not None:
            existing.acc_nav = acc_nav
        if daily_return is not None:
            existing.daily_return = daily_return
        return existing
    else:
        record = NavHistory(
            fund_id=fund_id,
            nav_date=nav_date,
            nav=nav,
            acc_nav=acc_nav,
            daily_return=daily_return,
        )
        db.add(record)
        return record


def update_fund_nav(db: Session, fund: Fund, days: int = 30) -> int:
    """
    更新单只基金的净值数据

    参数:
        db: 数据库会话
        fund: 基金对象
        days: 获取最近多少天的数据

    返回:
        更新的记录数
    """
    records = fetch_nav_history(fund.code, limit=days)
    if not records:
        return 0

    count = 0
    for r in records:
        save_nav_record(
            db,
            fund_id=fund.id,
            nav_date=r.nav_date,
            nav=r.nav,
            acc_nav=r.acc_nav,
            daily_return=r.day_growth,
        )
        count += 1

    db.flush()
    return count


def update_all_funds_nav(db: Session, days: int = 30) -> dict[str, int]:
    """
    更新所有基金的净值数据

    返回:
        {基金代码: 更新记录数}
    """
    funds = db.execute(select(Fund)).scalars().all()
    results = {}

    for fund in funds:
        try:
            count = update_fund_nav(db, fund, days)
            results[fund.code] = count
        except Exception as e:
            results[fund.code] = -1  # 表示失败

    return results
