"""
风险预测分析服务

基于历史数据分析未来走势，提供智能风险预测和投资建议。
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional
import math

from sqlalchemy.orm import Session

from app.data.models import Fund, NavHistory, Holding
from app.services.nav_service import get_nav_history


class TrendDirection(Enum):
    """趋势方向"""
    STRONG_UP = "强势上涨"
    UP = "上涨"
    SIDEWAYS = "震荡"
    DOWN = "下跌"
    STRONG_DOWN = "强势下跌"


class RiskLevel(Enum):
    """风险等级"""
    LOW = "低风险"
    MEDIUM_LOW = "中低风险"
    MEDIUM = "中等风险"
    MEDIUM_HIGH = "中高风险"
    HIGH = "高风险"


class InvestAction(Enum):
    """投资操作建议"""
    STRONG_BUY = "建议加仓"
    BUY = "可适当加仓"
    HOLD = "建议持有"
    REDUCE = "可适当减仓"
    STRONG_SELL = "建议减仓"
    WAIT = "观望等待"


@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    direction: TrendDirection
    strength: float  # 0-100，趋势强度
    ma5: Optional[float] = None  # 5日均线
    ma10: Optional[float] = None  # 10日均线
    ma20: Optional[float] = None  # 20日均线
    price_vs_ma5: Optional[float] = None  # 当前价格相对5日均线偏离 %
    price_vs_ma20: Optional[float] = None  # 当前价格相对20日均线偏离 %
    momentum: Optional[float] = None  # 动量指标
    rsi: Optional[float] = None  # RSI 相对强弱指标


@dataclass
class RiskForecast:
    """风险预测结果"""
    fund_code: str
    fund_name: str
    current_nav: float
    nav_date: date

    # 趋势分析
    trend: TrendDirection
    trend_strength: float
    trend_description: str

    # 风险评估
    risk_level: RiskLevel
    risk_score: int  # 0-100，越高风险越大
    risk_factors: list[str]  # 风险因素

    # 预测建议
    forecast_direction: str  # 预期走向
    confidence: float  # 预测置信度 0-100
    suggestion: str  # 操作建议

    # 技术指标
    volatility_trend: str  # 波动率趋势

    # 投资操作建议（有默认值的字段放在最后）
    invest_action: InvestAction = InvestAction.HOLD  # 投资操作
    action_reason: str = ""  # 操作理由
    action_detail: str = ""  # 详细说明
    support_level: Optional[float] = None  # 支撑位
    resistance_level: Optional[float] = None  # 阻力位


@dataclass
class InvestmentAdvice:
    """单只基金的投资建议"""
    fund_code: str
    fund_name: str
    current_nav: float
    nav_date: date

    # 操作建议
    action: InvestAction
    action_icon: str  # 操作图标
    action_reason: str  # 主要理由
    action_details: list[str]  # 详细分析点

    # 技术面分析
    trend_analysis: str  # 趋势分析
    technical_signals: list[str]  # 技术信号

    # 风险提示
    risk_level: RiskLevel
    risk_warnings: list[str]

    # 操作参考
    suggested_ratio: str  # 建议操作比例
    price_reference: str  # 价格参考
    time_horizon: str  # 时间周期建议


@dataclass
class PortfolioInvestmentAdvice:
    """组合整体投资建议"""
    report_date: date
    overall_sentiment: str  # 整体情绪：乐观/谨慎/悲观
    market_view: str  # 市场观点

    # 操作汇总
    buy_recommendations: list[InvestmentAdvice]  # 建议加仓
    hold_recommendations: list[InvestmentAdvice]  # 建议持有
    sell_recommendations: list[InvestmentAdvice]  # 建议减仓

    # 整体建议
    portfolio_action: str  # 组合操作建议
    key_points: list[str]  # 核心要点
    risk_reminders: list[str]  # 风险提醒

    # 详细分析
    fund_advices: list[InvestmentAdvice]  # 各基金建议


@dataclass
class PortfolioRiskForecast:
    """组合风险预测"""
    overall_risk_level: RiskLevel
    overall_risk_score: int
    risk_description: str

    # 组合分析
    bullish_funds: int  # 看涨基金数
    bearish_funds: int  # 看跌基金数
    neutral_funds: int  # 震荡基金数

    # 风险警示
    warnings: list[str]
    suggestions: list[str]

    # 各基金预测
    fund_forecasts: list[RiskForecast]


def calculate_ma(prices: list[float], period: int) -> Optional[float]:
    """计算移动平均线"""
    if len(prices) < period:
        return None
    return sum(prices[:period]) / period


def calculate_momentum(prices: list[float], period: int = 10) -> Optional[float]:
    """
    计算动量指标
    动量 = (当前价格 - N日前价格) / N日前价格 * 100
    """
    if len(prices) < period + 1:
        return None
    return (prices[0] - prices[period]) / prices[period] * 100


def calculate_rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """
    计算RSI相对强弱指标
    RSI = 100 - 100 / (1 + RS)
    RS = 平均涨幅 / 平均跌幅
    """
    if len(prices) < period + 1:
        return None

    gains = []
    losses = []

    # 按时间正序计算涨跌
    for i in range(1, min(period + 1, len(prices))):
        change = prices[i-1] - prices[i]  # prices是降序的
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def calculate_volatility_trend(nav_list: list[NavHistory]) -> str:
    """
    分析波动率趋势
    比较近期波动率与历史波动率
    """
    if len(nav_list) < 20:
        return "数据不足"

    # 计算近10日波动率
    recent_navs = [float(n.nav) for n in nav_list[:10]]
    recent_returns = [(recent_navs[i] - recent_navs[i+1]) / recent_navs[i+1]
                      for i in range(len(recent_navs)-1)]
    recent_vol = math.sqrt(sum(r**2 for r in recent_returns) / len(recent_returns)) if recent_returns else 0

    # 计算历史波动率（10-30日）
    if len(nav_list) >= 30:
        hist_navs = [float(n.nav) for n in nav_list[10:30]]
        hist_returns = [(hist_navs[i] - hist_navs[i+1]) / hist_navs[i+1]
                        for i in range(len(hist_navs)-1)]
        hist_vol = math.sqrt(sum(r**2 for r in hist_returns) / len(hist_returns)) if hist_returns else 0

        if hist_vol > 0:
            vol_change = (recent_vol - hist_vol) / hist_vol
            if vol_change > 0.3:
                return "波动加剧 ⚠️"
            elif vol_change < -0.3:
                return "波动收敛 ✓"

    return "波动平稳"


def find_support_resistance(prices: list[float]) -> tuple[Optional[float], Optional[float]]:
    """
    寻找支撑位和阻力位
    使用近期的低点和高点
    """
    if len(prices) < 10:
        return None, None

    recent_prices = prices[:20] if len(prices) >= 20 else prices

    # 支撑位：近期最低点
    support = min(recent_prices)
    # 阻力位：近期最高点
    resistance = max(recent_prices)

    return round(support, 4), round(resistance, 4)


def analyze_trend(nav_list: list[NavHistory]) -> TrendAnalysis:
    """
    分析基金趋势
    """
    if len(nav_list) < 5:
        return TrendAnalysis(
            direction=TrendDirection.SIDEWAYS,
            strength=0,
        )

    # 提取价格（降序，最新在前）
    prices = [float(n.nav) for n in nav_list]
    current_price = prices[0]

    # 计算均线
    ma5 = calculate_ma(prices, 5)
    ma10 = calculate_ma(prices, 10)
    ma20 = calculate_ma(prices, 20)

    # 计算偏离度
    price_vs_ma5 = ((current_price - ma5) / ma5 * 100) if ma5 else None
    price_vs_ma20 = ((current_price - ma20) / ma20 * 100) if ma20 else None

    # 计算动量和RSI
    momentum = calculate_momentum(prices, 10)
    rsi = calculate_rsi(prices, 14)

    # 综合判断趋势方向和强度
    strength = 50.0  # 基准强度
    direction = TrendDirection.SIDEWAYS

    # 基于均线排列判断
    if ma5 and ma10 and ma20:
        if ma5 > ma10 > ma20:
            direction = TrendDirection.UP
            strength += 20
        elif ma5 < ma10 < ma20:
            direction = TrendDirection.DOWN
            strength -= 20

    # 基于价格位置调整
    if price_vs_ma5:
        if price_vs_ma5 > 3:
            strength += 15
        elif price_vs_ma5 < -3:
            strength -= 15

    # 基于动量调整
    if momentum:
        if momentum > 5:
            strength += 15
            if direction == TrendDirection.UP:
                direction = TrendDirection.STRONG_UP
        elif momentum < -5:
            strength -= 15
            if direction == TrendDirection.DOWN:
                direction = TrendDirection.STRONG_DOWN

    # 基于RSI调整
    if rsi:
        if rsi > 70:
            strength += 10  # 超买区域
        elif rsi < 30:
            strength -= 10  # 超卖区域

    # 限制范围
    strength = max(0, min(100, strength))

    return TrendAnalysis(
        direction=direction,
        strength=round(strength, 1),
        ma5=round(ma5, 4) if ma5 else None,
        ma10=round(ma10, 4) if ma10 else None,
        ma20=round(ma20, 4) if ma20 else None,
        price_vs_ma5=round(price_vs_ma5, 2) if price_vs_ma5 else None,
        price_vs_ma20=round(price_vs_ma20, 2) if price_vs_ma20 else None,
        momentum=round(momentum, 2) if momentum else None,
        rsi=rsi,
    )


def forecast_fund_risk(db: Session, fund: Fund, days: int = 60) -> Optional[RiskForecast]:
    """
    预测单只基金的风险
    """
    nav_list = get_nav_history(db, fund.id, limit=days)
    if not nav_list or len(nav_list) < 5:
        return None

    current_nav = float(nav_list[0].nav)
    nav_date = nav_list[0].nav_date
    prices = [float(n.nav) for n in nav_list]

    # 趋势分析
    trend_analysis = analyze_trend(nav_list)

    # 波动率趋势
    vol_trend = calculate_volatility_trend(nav_list)

    # 支撑位/阻力位
    support, resistance = find_support_resistance(prices)

    # 计算风险分数
    risk_score = 50  # 基准分
    risk_factors = []

    # 基于趋势调整风险
    if trend_analysis.direction == TrendDirection.STRONG_DOWN:
        risk_score += 25
        risk_factors.append("处于强势下跌趋势")
    elif trend_analysis.direction == TrendDirection.DOWN:
        risk_score += 15
        risk_factors.append("处于下跌趋势")
    elif trend_analysis.direction == TrendDirection.STRONG_UP:
        risk_score -= 10

    # 基于RSI调整
    if trend_analysis.rsi:
        if trend_analysis.rsi > 80:
            risk_score += 20
            risk_factors.append(f"RSI={trend_analysis.rsi}，严重超买，回调风险大")
        elif trend_analysis.rsi > 70:
            risk_score += 10
            risk_factors.append(f"RSI={trend_analysis.rsi}，超买区域")
        elif trend_analysis.rsi < 20:
            risk_score += 15
            risk_factors.append(f"RSI={trend_analysis.rsi}，严重超卖，可能继续探底")
        elif trend_analysis.rsi < 30:
            risk_factors.append(f"RSI={trend_analysis.rsi}，超卖区域，可能反弹")

    # 基于波动率调整
    if "加剧" in vol_trend:
        risk_score += 15
        risk_factors.append("近期波动明显加大")

    # 基于价格位置调整
    if trend_analysis.price_vs_ma20:
        if trend_analysis.price_vs_ma20 < -10:
            risk_score += 10
            risk_factors.append(f"价格较20日均线偏离{trend_analysis.price_vs_ma20}%")
        elif trend_analysis.price_vs_ma20 > 10:
            risk_score += 5
            risk_factors.append(f"价格高于20日均线{trend_analysis.price_vs_ma20}%，追高风险")

    # 限制范围
    risk_score = max(0, min(100, risk_score))

    # 确定风险等级
    if risk_score < 30:
        risk_level = RiskLevel.LOW
    elif risk_score < 45:
        risk_level = RiskLevel.MEDIUM_LOW
    elif risk_score < 60:
        risk_level = RiskLevel.MEDIUM
    elif risk_score < 75:
        risk_level = RiskLevel.MEDIUM_HIGH
    else:
        risk_level = RiskLevel.HIGH

    # 生成趋势描述
    trend_desc = f"当前{trend_analysis.direction.value}"
    if trend_analysis.ma5 and trend_analysis.ma20:
        if trend_analysis.ma5 > trend_analysis.ma20:
            trend_desc += "，短期均线在长期均线上方，多头排列"
        else:
            trend_desc += "，短期均线在长期均线下方，空头排列"

    # 预测方向
    if trend_analysis.direction in [TrendDirection.STRONG_UP, TrendDirection.UP]:
        forecast_dir = "预计短期内维持上涨趋势"
        if trend_analysis.rsi and trend_analysis.rsi > 70:
            forecast_dir = "短期可能出现回调整理"
    elif trend_analysis.direction in [TrendDirection.STRONG_DOWN, TrendDirection.DOWN]:
        forecast_dir = "预计短期内继续调整"
        if trend_analysis.rsi and trend_analysis.rsi < 30:
            forecast_dir = "可能出现技术性反弹"
    else:
        forecast_dir = "预计维持震荡走势"

    # 置信度
    confidence = 50 + (trend_analysis.strength - 50) * 0.5
    confidence = max(30, min(85, confidence))

    # 操作建议
    if risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM_HIGH]:
        suggestion = "建议谨慎，可考虑降低仓位或设置止损"
    elif risk_level == RiskLevel.MEDIUM:
        suggestion = "风险适中，建议持有观望，关注关键点位"
    elif risk_level == RiskLevel.MEDIUM_LOW:
        suggestion = "风险较低，可继续持有"
    else:
        suggestion = "风险较低，趋势良好"

    if not risk_factors:
        risk_factors.append("暂无明显风险信号")

    return RiskForecast(
        fund_code=fund.code,
        fund_name=fund.name,
        current_nav=current_nav,
        nav_date=nav_date,
        trend=trend_analysis.direction,
        trend_strength=trend_analysis.strength,
        trend_description=trend_desc,
        risk_level=risk_level,
        risk_score=risk_score,
        risk_factors=risk_factors,
        forecast_direction=forecast_dir,
        confidence=round(confidence, 1),
        suggestion=suggestion,
        volatility_trend=vol_trend,
        support_level=support,
        resistance_level=resistance,
    )


def forecast_portfolio_risk(db: Session) -> Optional[PortfolioRiskForecast]:
    """
    预测组合整体风险
    """
    holdings = db.query(Holding).all()
    if not holdings:
        return None

    fund_forecasts = []
    risk_scores = []
    warnings = []
    suggestions = []

    bullish = 0
    bearish = 0
    neutral = 0

    # 获取每只基金的预测
    fund_ids = set()
    for h in holdings:
        if h.fund_id in fund_ids:
            continue
        fund_ids.add(h.fund_id)

        forecast = forecast_fund_risk(db, h.fund)
        if forecast:
            fund_forecasts.append(forecast)
            risk_scores.append(forecast.risk_score)

            # 统计趋势分布
            if forecast.trend in [TrendDirection.STRONG_UP, TrendDirection.UP]:
                bullish += 1
            elif forecast.trend in [TrendDirection.STRONG_DOWN, TrendDirection.DOWN]:
                bearish += 1
            else:
                neutral += 1

            # 收集高风险警告
            if forecast.risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM_HIGH]:
                warnings.append(f"⚠️ {forecast.fund_name}：{forecast.risk_level.value}，{forecast.forecast_direction}")

    if not fund_forecasts:
        return None

    # 计算组合整体风险
    avg_risk = sum(risk_scores) / len(risk_scores)

    # 如果大部分基金看跌，风险加权
    if bearish > bullish:
        avg_risk = min(100, avg_risk * 1.2)

    overall_risk_score = int(avg_risk)

    # 确定整体风险等级
    if overall_risk_score < 30:
        overall_risk_level = RiskLevel.LOW
    elif overall_risk_score < 45:
        overall_risk_level = RiskLevel.MEDIUM_LOW
    elif overall_risk_score < 60:
        overall_risk_level = RiskLevel.MEDIUM
    elif overall_risk_score < 75:
        overall_risk_level = RiskLevel.MEDIUM_HIGH
    else:
        overall_risk_level = RiskLevel.HIGH

    # 生成描述
    total = bullish + bearish + neutral
    risk_desc = f"组合中{bullish}只基金呈上涨趋势，{bearish}只下跌趋势，{neutral}只震荡。"

    if bearish > total * 0.5:
        risk_desc += "整体偏空，建议控制仓位。"
        suggestions.append("多数持仓处于下跌趋势，建议审视持仓结构")
    elif bullish > total * 0.5:
        risk_desc += "整体偏多，可继续持有。"
        suggestions.append("多数持仓趋势良好，可适度持有")
    else:
        risk_desc += "市场分化明显，建议保持谨慎。"
        suggestions.append("市场方向不明，建议观望为主")

    # 集中度警告
    if len(fund_ids) <= 2:
        warnings.append("⚠️ 持仓基金数量过少，分散化不足")
        suggestions.append("建议增加基金数量以分散风险")

    if not warnings:
        warnings.append("✓ 暂无重大风险预警")

    if not suggestions:
        suggestions.append("继续关注市场变化，定期检视组合")

    return PortfolioRiskForecast(
        overall_risk_level=overall_risk_level,
        overall_risk_score=overall_risk_score,
        risk_description=risk_desc,
        bullish_funds=bullish,
        bearish_funds=bearish,
        neutral_funds=neutral,
        warnings=warnings,
        suggestions=suggestions,
        fund_forecasts=fund_forecasts,
    )


def determine_invest_action(
    trend: TrendDirection,
    rsi: Optional[float],
    risk_score: int,
    price_vs_ma20: Optional[float],
    vol_trend: str,
) -> tuple[InvestAction, str, str]:
    """
    综合技术指标确定投资操作建议

    返回: (操作建议, 主要理由, 详细说明)
    """
    action = InvestAction.HOLD
    reason = ""
    detail = ""

    # 核心决策逻辑
    bullish_signals = 0
    bearish_signals = 0
    signals = []

    # 1. 趋势判断（权重最高）
    if trend == TrendDirection.STRONG_UP:
        bullish_signals += 3
        signals.append("强势上涨趋势形成")
    elif trend == TrendDirection.UP:
        bullish_signals += 2
        signals.append("上涨趋势中")
    elif trend == TrendDirection.STRONG_DOWN:
        bearish_signals += 3
        signals.append("强势下跌趋势")
    elif trend == TrendDirection.DOWN:
        bearish_signals += 2
        signals.append("下跌趋势中")
    else:
        signals.append("震荡整理中")

    # 2. RSI 超买超卖判断
    if rsi is not None:
        if rsi < 25:
            bullish_signals += 2
            signals.append(f"RSI={rsi:.0f}，严重超卖，反弹概率大")
        elif rsi < 35:
            bullish_signals += 1
            signals.append(f"RSI={rsi:.0f}，超卖区域")
        elif rsi > 80:
            bearish_signals += 2
            signals.append(f"RSI={rsi:.0f}，严重超买，回调风险高")
        elif rsi > 70:
            bearish_signals += 1
            signals.append(f"RSI={rsi:.0f}，超买区域")

    # 3. 均线位置判断
    if price_vs_ma20 is not None:
        if price_vs_ma20 < -8:
            bullish_signals += 1
            signals.append(f"价格较20日均线低{abs(price_vs_ma20):.1f}%，有反弹空间")
        elif price_vs_ma20 > 8:
            bearish_signals += 1
            signals.append(f"价格较20日均线高{price_vs_ma20:.1f}%，追高风险")

    # 4. 波动率考量
    if "加剧" in vol_trend:
        bearish_signals += 1
        signals.append("近期波动加剧，不确定性增加")

    # 5. 风险分数考量
    if risk_score > 70:
        bearish_signals += 1
        signals.append("综合风险评分较高")
    elif risk_score < 35:
        bullish_signals += 1
        signals.append("综合风险评分较低")

    # 综合决策
    net_score = bullish_signals - bearish_signals

    if net_score >= 4:
        action = InvestAction.STRONG_BUY
        reason = "多项技术指标共振看涨"
        detail = "趋势向上且处于超卖区域，建议积极加仓，可分批买入"
    elif net_score >= 2:
        action = InvestAction.BUY
        reason = "技术面偏多"
        detail = "整体趋势向好，可适当加仓，注意控制节奏"
    elif net_score <= -4:
        action = InvestAction.STRONG_SELL
        reason = "多项技术指标共振看跌"
        detail = "趋势向下且风险较高，建议及时减仓止损"
    elif net_score <= -2:
        action = InvestAction.REDUCE
        reason = "技术面偏空"
        detail = "下跌趋势中或存在回调风险，可适当减仓"
    elif trend == TrendDirection.SIDEWAYS:
        action = InvestAction.WAIT
        reason = "方向不明确"
        detail = "震荡整理中，建议观望等待突破方向"
    else:
        action = InvestAction.HOLD
        reason = "维持现有仓位"
        detail = "多空力量均衡，建议持有观察"

    return action, reason, detail


def generate_fund_investment_advice(db: Session, fund: Fund) -> Optional[InvestmentAdvice]:
    """
    为单只基金生成详细的投资建议
    """
    # 获取风险预测
    forecast = forecast_fund_risk(db, fund, days=60)
    if not forecast:
        return None

    # 获取趋势分析
    nav_list = get_nav_history(db, fund.id, limit=60)
    if not nav_list:
        return None

    trend_analysis = analyze_trend(nav_list)

    # 确定投资操作
    action, action_reason, action_detail = determine_invest_action(
        trend=forecast.trend,
        rsi=trend_analysis.rsi,
        risk_score=forecast.risk_score,
        price_vs_ma20=trend_analysis.price_vs_ma20,
        vol_trend=forecast.volatility_trend,
    )

    # 生成操作图标
    action_icons = {
        InvestAction.STRONG_BUY: "🟢🟢",
        InvestAction.BUY: "🟢",
        InvestAction.HOLD: "🟡",
        InvestAction.REDUCE: "🟠",
        InvestAction.STRONG_SELL: "🔴",
        InvestAction.WAIT: "⚪",
    }
    action_icon = action_icons.get(action, "⚪")

    # 技术信号汇总
    technical_signals = []
    if trend_analysis.ma5 and trend_analysis.ma10 and trend_analysis.ma20:
        if trend_analysis.ma5 > trend_analysis.ma10 > trend_analysis.ma20:
            technical_signals.append("均线多头排列")
        elif trend_analysis.ma5 < trend_analysis.ma10 < trend_analysis.ma20:
            technical_signals.append("均线空头排列")
        else:
            technical_signals.append("均线交织")

    if trend_analysis.rsi:
        if trend_analysis.rsi > 70:
            technical_signals.append(f"RSI {trend_analysis.rsi:.0f} 超买")
        elif trend_analysis.rsi < 30:
            technical_signals.append(f"RSI {trend_analysis.rsi:.0f} 超卖")
        else:
            technical_signals.append(f"RSI {trend_analysis.rsi:.0f} 中性")

    if trend_analysis.momentum:
        if trend_analysis.momentum > 5:
            technical_signals.append(f"动量 +{trend_analysis.momentum:.1f}% 强势")
        elif trend_analysis.momentum < -5:
            technical_signals.append(f"动量 {trend_analysis.momentum:.1f}% 弱势")

    technical_signals.append(forecast.volatility_trend)

    # 详细分析点
    action_details = [action_detail]
    action_details.extend(forecast.risk_factors[:3])  # 取前3个风险因素

    # 趋势分析文字
    trend_text = f"{forecast.trend.value}，趋势强度 {forecast.trend_strength:.0f}/100。{forecast.trend_description}"

    # 操作比例建议
    if action in [InvestAction.STRONG_BUY]:
        suggested_ratio = "可加仓 30%-50%"
    elif action == InvestAction.BUY:
        suggested_ratio = "可加仓 10%-20%"
    elif action == InvestAction.REDUCE:
        suggested_ratio = "可减仓 10%-20%"
    elif action == InvestAction.STRONG_SELL:
        suggested_ratio = "建议减仓 30%-50%"
    else:
        suggested_ratio = "维持现有仓位"

    # 价格参考
    price_ref_parts = []
    if forecast.support_level:
        price_ref_parts.append(f"支撑位 ¥{forecast.support_level:.4f}")
    if forecast.resistance_level:
        price_ref_parts.append(f"阻力位 ¥{forecast.resistance_level:.4f}")
    price_reference = "，".join(price_ref_parts) if price_ref_parts else "暂无明确支撑阻力位"

    # 时间周期
    if action in [InvestAction.STRONG_BUY, InvestAction.STRONG_SELL]:
        time_horizon = "建议本周内操作"
    elif action in [InvestAction.BUY, InvestAction.REDUCE]:
        time_horizon = "可在1-2周内逐步操作"
    else:
        time_horizon = "持续观察，无需急于操作"

    return InvestmentAdvice(
        fund_code=fund.code,
        fund_name=fund.name,
        current_nav=forecast.current_nav,
        nav_date=forecast.nav_date,
        action=action,
        action_icon=action_icon,
        action_reason=action_reason,
        action_details=action_details,
        trend_analysis=trend_text,
        technical_signals=technical_signals,
        risk_level=forecast.risk_level,
        risk_warnings=forecast.risk_factors,
        suggested_ratio=suggested_ratio,
        price_reference=price_reference,
        time_horizon=time_horizon,
    )


def generate_portfolio_investment_advice(db: Session) -> Optional[PortfolioInvestmentAdvice]:
    """
    生成组合整体投资建议报告
    """
    from datetime import date as date_type

    holdings = db.query(Holding).all()
    if not holdings:
        return None

    # 获取所有持仓基金的投资建议
    fund_advices = []
    buy_recommendations = []
    hold_recommendations = []
    sell_recommendations = []

    fund_ids = set()
    for h in holdings:
        if h.fund_id in fund_ids:
            continue
        fund_ids.add(h.fund_id)

        advice = generate_fund_investment_advice(db, h.fund)
        if advice:
            fund_advices.append(advice)

            if advice.action in [InvestAction.STRONG_BUY, InvestAction.BUY]:
                buy_recommendations.append(advice)
            elif advice.action in [InvestAction.STRONG_SELL, InvestAction.REDUCE]:
                sell_recommendations.append(advice)
            else:
                hold_recommendations.append(advice)

    if not fund_advices:
        return None

    # 确定整体情绪
    buy_count = len(buy_recommendations)
    sell_count = len(sell_recommendations)
    total = len(fund_advices)

    if buy_count > total * 0.6:
        overall_sentiment = "乐观"
        market_view = "多数持仓基金趋势向好，市场情绪偏多，可考虑适度进取"
    elif sell_count > total * 0.6:
        overall_sentiment = "谨慎"
        market_view = "多数持仓基金趋势偏弱，市场承压，建议防守为主"
    elif sell_count > buy_count:
        overall_sentiment = "偏谨慎"
        market_view = "市场分化，整体偏弱，建议控制仓位"
    elif buy_count > sell_count:
        overall_sentiment = "偏乐观"
        market_view = "市场分化，整体偏强，可适度参与"
    else:
        overall_sentiment = "中性"
        market_view = "多空力量均衡，方向不明，建议观望为主"

    # 组合操作建议
    if buy_count > sell_count * 2:
        portfolio_action = "整体可适度加仓，优先考虑趋势向好的品种"
    elif sell_count > buy_count * 2:
        portfolio_action = "整体建议减仓或调仓，降低风险敞口"
    elif buy_count > 0 and sell_count > 0:
        portfolio_action = "建议结构性调仓：减持弱势品种，增持强势品种"
    else:
        portfolio_action = "维持现有配置，持续观察市场变化"

    # 核心要点
    key_points = []
    if buy_recommendations:
        top_buy = buy_recommendations[0]
        key_points.append(f"【加仓首选】{top_buy.fund_name}：{top_buy.action_reason}")
    if sell_recommendations:
        top_sell = sell_recommendations[0]
        key_points.append(f"【减仓提醒】{top_sell.fund_name}：{top_sell.action_reason}")
    if not key_points:
        key_points.append("当前持仓整体平稳，无明显加减仓信号")

    # 统计信息
    key_points.append(f"组合中 {buy_count} 只建议加仓，{len(hold_recommendations)} 只建议持有，{sell_count} 只建议减仓")

    # 风险提醒
    risk_reminders = [
        "以上建议基于技术分析，不构成投资建议",
        "投资有风险，入市需谨慎",
        "建议结合自身风险承受能力和资金情况做出决策",
    ]

    # 检查是否有高风险基金
    high_risk_funds = [a for a in fund_advices if a.risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM_HIGH]]
    if high_risk_funds:
        risk_reminders.insert(0, f"⚠️ {len(high_risk_funds)} 只基金处于中高风险状态，请重点关注")

    return PortfolioInvestmentAdvice(
        report_date=date_type.today(),
        overall_sentiment=overall_sentiment,
        market_view=market_view,
        buy_recommendations=buy_recommendations,
        hold_recommendations=hold_recommendations,
        sell_recommendations=sell_recommendations,
        portfolio_action=portfolio_action,
        key_points=key_points,
        risk_reminders=risk_reminders,
        fund_advices=fund_advices,
    )
