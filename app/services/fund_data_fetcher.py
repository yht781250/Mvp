"""
基金数据抓取服务

从公开数据源获取基金信息和净值数据。
数据源：天天基金网（eastmoney）
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import requests


@dataclass
class FundInfo:
    """基金基本信息"""
    code: str
    name: str
    fund_type: str  # 基金类型
    nav: Optional[Decimal] = None  # 最新净值
    nav_date: Optional[date] = None  # 净值日期
    day_growth: Optional[Decimal] = None  # 日涨跌幅


@dataclass
class NavRecord:
    """净值记录"""
    nav_date: date
    nav: Decimal
    acc_nav: Optional[Decimal] = None  # 累计净值
    day_growth: Optional[Decimal] = None  # 日涨跌幅(%)


class FundDataFetcher:
    """基金数据抓取器"""

    # 基金基本信息接口
    FUND_INFO_URL = "http://fundgz.1234567.com.cn/js/{code}.js"
    # 基金详情接口
    FUND_DETAIL_URL = "http://fund.eastmoney.com/pingzhongdata/{code}.js"
    # 历史净值接口
    NAV_HISTORY_URL = "http://fund.eastmoney.com/f10/F10DataApi.aspx"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://fund.eastmoney.com/",
        })

    def get_fund_info(self, code: str) -> Optional[FundInfo]:
        """
        获取基金基本信息

        参数:
            code: 基金代码，如 "000001"

        返回:
            FundInfo 或 None（获取失败时）
        """
        code = code.strip()
        if not code:
            return None

        try:
            # 尝试从实时估值接口获取
            url = self.FUND_INFO_URL.format(code=code)
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()

            # 解析 jsonp 格式: jsonpgz({"fundcode":"000001","name":"华夏成长混合",...});
            text = resp.text
            match = re.search(r'jsonpgz\((.*?)\);', text)
            if match:
                import json
                data = json.loads(match.group(1))
                return FundInfo(
                    code=data.get("fundcode", code),
                    name=data.get("name", ""),
                    fund_type="",  # 此接口不返回类型
                    nav=Decimal(str(data.get("dwjz", 0))) if data.get("dwjz") else None,
                    nav_date=datetime.strptime(data.get("jzrq", ""), "%Y-%m-%d").date() if data.get("jzrq") else None,
                    day_growth=Decimal(str(data.get("gszzl", 0))) if data.get("gszzl") else None,
                )

            # 如果实时接口失败，尝试详情接口
            return self._get_fund_info_from_detail(code)

        except Exception:
            # 尝试备用方法
            return self._get_fund_info_from_detail(code)

    def _get_fund_info_from_detail(self, code: str) -> Optional[FundInfo]:
        """从详情页获取基金信息（备用方法）"""
        try:
            url = self.FUND_DETAIL_URL.format(code=code)
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            text = resp.text

            # 提取基金名称
            name_match = re.search(r'fS_name\s*=\s*"([^"]+)"', text)
            name = name_match.group(1) if name_match else ""

            if not name:
                return None

            # 提取基金代码
            code_match = re.search(r'fS_code\s*=\s*"([^"]+)"', text)
            fund_code = code_match.group(1) if code_match else code

            return FundInfo(
                code=fund_code,
                name=name,
                fund_type="",
            )

        except Exception:
            return None

    def get_nav_history(
        self,
        code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 30,
    ) -> list[NavRecord]:
        """
        获取历史净值数据

        参数:
            code: 基金代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            limit: 返回条数限制

        返回:
            净值记录列表，按日期降序
        """
        code = code.strip()
        if not code:
            return []

        try:
            params = {
                "type": "lsjz",
                "code": code,
                "per": limit,
                "page": 1,
            }
            if start_date:
                params["sdate"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["edate"] = end_date.strftime("%Y-%m-%d")

            resp = self.session.get(self.NAV_HISTORY_URL, params=params, timeout=self.timeout)
            resp.raise_for_status()

            # 解析 HTML 表格
            records = []
            # 匹配表格行
            rows = re.findall(r'<tr>(.*?)</tr>', resp.text, re.DOTALL)
            for row in rows:
                cols = re.findall(r'<td[^>]*>(.*?)</td>', row)
                if len(cols) >= 3:
                    try:
                        nav_date_str = cols[0].strip()
                        nav_str = cols[1].strip()
                        acc_nav_str = cols[2].strip() if len(cols) > 2 else None
                        growth_str = cols[3].strip() if len(cols) > 3 else None

                        # 跳过无效数据
                        if not nav_date_str or not nav_str:
                            continue
                        if nav_str == "--" or nav_str == "":
                            continue

                        nav_date_val = datetime.strptime(nav_date_str, "%Y-%m-%d").date()
                        nav_val = Decimal(nav_str)
                        acc_nav_val = Decimal(acc_nav_str) if acc_nav_str and acc_nav_str != "--" else None

                        # 解析涨跌幅
                        growth_val = None
                        if growth_str and growth_str != "--" and growth_str != "":
                            growth_str = growth_str.replace("%", "").strip()
                            if growth_str:
                                growth_val = Decimal(growth_str)

                        records.append(NavRecord(
                            nav_date=nav_date_val,
                            nav=nav_val,
                            acc_nav=acc_nav_val,
                            day_growth=growth_val,
                        ))
                    except (ValueError, IndexError):
                        continue

            return records

        except Exception:
            return []


# 全局实例
_fetcher: Optional[FundDataFetcher] = None


def get_fetcher() -> FundDataFetcher:
    """获取全局抓取器实例"""
    global _fetcher
    if _fetcher is None:
        _fetcher = FundDataFetcher()
    return _fetcher


def fetch_fund_info(code: str) -> Optional[FundInfo]:
    """获取基金信息（便捷函数）"""
    return get_fetcher().get_fund_info(code)


def fetch_nav_history(code: str, limit: int = 30) -> list[NavRecord]:
    """获取历史净值（便捷函数）"""
    return get_fetcher().get_nav_history(code, limit=limit)
