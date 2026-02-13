from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from app.core.settings import settings
from app.services.fund_data_fetcher import fetch_fund_info


app = FastAPI(title=settings.app_name, version=settings.app_version)

# 添加 CORS 支持，允许 Streamlit 前端调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FundInfoResponse(BaseModel):
    """基金信息响应"""
    code: str
    name: str
    nav: Optional[float] = None
    nav_date: Optional[str] = None
    day_growth: Optional[float] = None


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "message": "服务已启动",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/fund/{code}", response_model=FundInfoResponse)
def get_fund_info(code: str):
    """
    根据基金代码获取基金信息

    - **code**: 6位基金代码，如 000001
    """
    if not code or len(code) != 6:
        raise HTTPException(status_code=400, detail="基金代码必须为6位数字")

    info = fetch_fund_info(code)
    if not info:
        raise HTTPException(status_code=404, detail=f"未找到基金：{code}")

    return FundInfoResponse(
        code=info.code,
        name=info.name,
        nav=float(info.nav) if info.nav else None,
        nav_date=info.nav_date.strftime("%Y-%m-%d") if info.nav_date else None,
        day_growth=float(info.day_growth) if info.day_growth else None,
    )
