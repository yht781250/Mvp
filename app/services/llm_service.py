"""
LLM 服务层

提供与 OpenAI 兼容接口的大语言模型交互功能。
用于生成可读的投资分析解释，不直接给出买卖建议。
"""

from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from app.core.settings import settings
from app.services.rules_engine import RuleResult


@dataclass
class LLMResponse:
    """LLM 响应结果"""
    success: bool
    content: str
    model: str = ""
    error: Optional[str] = None


def get_llm_client() -> Optional[OpenAI]:
    """
    获取 LLM 客户端

    返回 OpenAI 客户端实例，如果未配置则返回 None
    """
    if not settings.llm_base_url or not settings.llm_api_key:
        return None

    return OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )


def is_llm_configured() -> bool:
    """检查 LLM 是否已配置"""
    return bool(settings.llm_base_url and settings.llm_api_key and settings.llm_model)


# ============ 系统提示词 ============

SYSTEM_PROMPT = """你是一位专业、理性的基金投资分析助手。你的职责是：

1. 基于规则引擎产出的诊断结论，用通俗易懂的语言向用户解释
2. 提供客观、中立的分析视角，不做主观投资建议
3. 始终强调风险提示，保护投资者利益

你的回答风格：
- 专业但不艰涩，用大白话讲清楚复杂概念
- 理性冷静，基于数据说话
- 每次回答都要包含风险提示
- 不使用"保本"、"稳赚"等违规词汇
- 不直接告诉用户"买"或"卖"，只提供分析参考

输出格式：
- 使用 Markdown 格式
- 重点内容用 **粗体** 标注
- 分点阐述，逻辑清晰"""


# ============ LLM 调用函数 ============

def generate_analysis_summary(
    portfolio_summary: str,
    rule_results: list[RuleResult],
    temperature: float = 0.3,
) -> LLMResponse:
    """
    生成组合分析摘要

    参数:
        portfolio_summary: 组合概况文本
        rule_results: 规则检查结果列表
        temperature: 生成温度（0-1，越低越确定）

    返回:
        LLMResponse 对象
    """
    client = get_llm_client()
    if not client:
        return LLMResponse(
            success=False,
            content="",
            error="LLM 未配置，请在【⚙️ 系统信息 → LLM配置】中设置 API 地址、密钥和模型",
        )

    # 构建规则结果文本
    rules_text = ""
    if rule_results:
        rules_text = "## 风险预警\n\n"
        for r in rule_results:
            rules_text += f"### {r.title}\n"
            rules_text += f"- 诊断：{r.diagnosis}\n"
            rules_text += f"- 依据：{r.trigger_basis}\n"
            rules_text += f"- 建议：{r.suggestion}\n\n"
    else:
        rules_text = "## 风险预警\n\n当前组合未触发任何风险预警规则。\n"

    user_prompt = f"""请基于以下组合数据和风险预警，生成一份简洁的投资分析报告。

{portfolio_summary}

{rules_text}

要求：
1. 总结当前组合的整体状况（2-3句话）
2. 针对每条预警，用通俗语言解释其含义和潜在影响
3. 给出综合性的观察建议（注意：不是买卖建议）
4. 以风险提示结尾"""

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=1500,
        )

        content = response.choices[0].message.content
        return LLMResponse(
            success=True,
            content=content,
            model=settings.llm_model,
        )

    except Exception as e:
        return LLMResponse(
            success=False,
            content="",
            error=f"LLM 调用失败：{str(e)}",
        )


def explain_single_warning(
    rule_result: RuleResult,
    temperature: float = 0.3,
) -> LLMResponse:
    """
    解释单条风险预警

    参数:
        rule_result: 规则检查结果
        temperature: 生成温度

    返回:
        LLMResponse 对象
    """
    client = get_llm_client()
    if not client:
        return LLMResponse(
            success=False,
            content="",
            error="LLM 未配置，请在【⚙️ 系统信息 → LLM配置】中设置",
        )

    user_prompt = f"""请用通俗易懂的语言解释以下风险预警：

**预警标题**：{rule_result.title}

**诊断结论**：{rule_result.diagnosis}

**触发依据**：{rule_result.trigger_basis}

**系统建议**：{rule_result.suggestion}

**风险提示**：{rule_result.risk_warning}

要求：
1. 用大白话解释这个预警意味着什么
2. 说明可能的影响和应对思路
3. 保持客观中立，不给出具体买卖建议
4. 控制在 200 字以内"""

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=500,
        )

        content = response.choices[0].message.content
        return LLMResponse(
            success=True,
            content=content,
            model=settings.llm_model,
        )

    except Exception as e:
        return LLMResponse(
            success=False,
            content="",
            error=f"LLM 调用失败：{str(e)}",
        )


def generate_daily_report(
    portfolio_summary: str,
    metrics_summary: str,
    rule_results: list[RuleResult],
    temperature: float = 0.3,
) -> LLMResponse:
    """
    生成每日投资报告

    参数:
        portfolio_summary: 组合概况
        metrics_summary: 指标概况
        rule_results: 规则检查结果
        temperature: 生成温度

    返回:
        LLMResponse 对象
    """
    client = get_llm_client()
    if not client:
        return LLMResponse(
            success=False,
            content="",
            error="LLM 未配置，请在【⚙️ 系统信息 → LLM配置】中设置",
        )

    # 构建预警摘要
    warnings_text = ""
    if rule_results:
        for r in rule_results:
            warnings_text += f"- [{r.level.value}] {r.title}: {r.diagnosis}\n"
    else:
        warnings_text = "- 无风险预警\n"

    user_prompt = f"""请生成一份简洁的每日投资观察报告。

## 组合概况
{portfolio_summary}

## 风险指标
{metrics_summary}

## 今日预警
{warnings_text}

请按以下格式输出：

# 📊 每日投资观察

## 今日概况
（2-3句话总结组合变化）

## 重点关注
（列出需要关注的事项）

## 观察建议
（给出客观的观察视角，不是买卖建议）

## ⚠️ 风险提示
（必须包含的风险提示语）"""

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=1000,
        )

        content = response.choices[0].message.content
        return LLMResponse(
            success=True,
            content=content,
            model=settings.llm_model,
        )

    except Exception as e:
        return LLMResponse(
            success=False,
            content="",
            error=f"LLM 调用失败：{str(e)}",
        )
