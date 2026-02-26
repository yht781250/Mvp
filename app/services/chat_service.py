"""
AI 对话服务层

提供基于净值数据上下文的多轮对话功能，支持自定义角色。
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.data.models import ChatMessage, ChatRole, ChatSession
from app.services.llm_service import LLMResponse, get_llm_client


# ============ 默认角色系统提示词 ============

DEFAULT_FINANCE_EXPERT_PROMPT = """你是一位资深金融投资分析专家，拥有CFA和FRM双重认证背景，专注于公募基金投资研究。

## 你的专业能力

1. **净值分析**：擅长解读基金净值走势、涨跌规律、波动特征
2. **趋势研判**：基于历史净值数据判断短期和中期趋势方向
3. **风险评估**：识别净值波动中的风险信号，评估回撤风险
4. **比较分析**：将基金表现与同类基金、基准指数进行对比
5. **投资策略**：根据净值走势提供定投、加仓、减仓等策略参考

## 回答规范

- 使用 Markdown 格式输出，重点内容用 **粗体** 标注
- 分析需引用具体数据，避免空泛结论
- 多角度分析：利好因素、风险因素、中性观察
- 给出明确的观点和逻辑推理过程
- 适当使用表格展示对比数据
- 语言专业但通俗易懂，避免过度使用术语

## 合规要求（必须遵守）

- 每次回答末尾必须附带风险提示
- 不得使用"保本"、"稳赚"、"零风险"等违规表述
- 不直接给出"买入"或"卖出"的指令性建议，只提供分析参考
- 必须强调"历史业绩不代表未来表现"
- 提醒用户关注自身风险承受能力

## 风险提示模板

> 以上分析基于历史净值数据，仅供研究参考，不构成投资建议。基金投资有风险，入市需谨慎。请根据自身风险承受能力做出投资决策。"""


# ============ 角色管理 ============

def get_all_roles(db: Session) -> list[ChatRole]:
    """获取所有对话角色"""
    return db.query(ChatRole).order_by(ChatRole.is_default.desc(), ChatRole.created_at).all()


def get_default_role(db: Session) -> Optional[ChatRole]:
    """获取默认角色"""
    return db.query(ChatRole).filter(ChatRole.is_default == True).first()


def get_role_by_id(db: Session, role_id: int) -> Optional[ChatRole]:
    """根据ID获取角色"""
    return db.query(ChatRole).filter(ChatRole.id == role_id).first()


def create_role(
    db: Session,
    name: str,
    description: str,
    system_prompt: str,
    temperature: float = 0.7,
    is_default: bool = False,
) -> ChatRole:
    """
    创建新角色

    如果设为默认角色，会取消其他角色的默认状态。
    """
    if is_default:
        _clear_default_flag(db)

    role = ChatRole(
        name=name,
        description=description,
        system_prompt=system_prompt,
        temperature=Decimal(str(temperature)),
        is_default=is_default,
        is_builtin=False,
    )
    db.add(role)
    db.flush()
    return role


def update_role(
    db: Session,
    role_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    is_default: Optional[bool] = None,
) -> Optional[ChatRole]:
    """更新角色配置"""
    role = get_role_by_id(db, role_id)
    if not role:
        return None

    if name is not None:
        role.name = name
    if description is not None:
        role.description = description
    if system_prompt is not None:
        role.system_prompt = system_prompt
    if temperature is not None:
        role.temperature = Decimal(str(temperature))
    if is_default is not None and is_default:
        _clear_default_flag(db)
        role.is_default = True

    db.flush()
    return role


def delete_role(db: Session, role_id: int) -> bool:
    """
    删除角色

    内置角色不可删除。如果删除的是默认角色，会将第一个内置角色设为默认。
    """
    role = get_role_by_id(db, role_id)
    if not role or role.is_builtin:
        return False

    was_default = role.is_default
    db.delete(role)
    db.flush()

    # 如果删除了默认角色，重新指定默认
    if was_default:
        first_role = db.query(ChatRole).order_by(ChatRole.is_builtin.desc(), ChatRole.id).first()
        if first_role:
            first_role.is_default = True
            db.flush()

    return True


def init_default_roles(db: Session) -> None:
    """
    初始化内置角色

    仅在角色表为空时执行，避免重复插入。
    """
    existing_count = db.query(ChatRole).count()
    if existing_count > 0:
        return

    builtin_role = ChatRole(
        name="金融投资分析专家",
        description="资深基金分析师，擅长净值分析、趋势研判、风险评估，提供专业投资分析参考",
        system_prompt=DEFAULT_FINANCE_EXPERT_PROMPT,
        temperature=Decimal("0.70"),
        is_default=True,
        is_builtin=True,
    )
    db.add(builtin_role)
    db.flush()


def _clear_default_flag(db: Session) -> None:
    """清除所有角色的默认标记"""
    db.query(ChatRole).filter(ChatRole.is_default == True).update({"is_default": False})


# ============ 对话功能 ============

def build_nav_context(
    fund_name: str,
    fund_code: str,
    nav_data: list[dict],
    realtime_info: Optional[dict] = None,
) -> str:
    """
    将净值数据构建为对话上下文文本

    参数:
        fund_name: 基金名称
        fund_code: 基金代码
        nav_data: 净值数据列表，格式 [{"日期", "单位净值", "累计净值", "日涨跌%"}]
        realtime_info: 实时估值信息，格式 {"latest_nav", "nav_date", "day_growth"}
    """
    if not nav_data:
        return f"基金：{fund_name}（{fund_code}），暂无净值数据。"

    context = f"## 当前分析基金：{fund_name}（{fund_code}）\n\n"

    # 今日实时估值信息
    if realtime_info:
        query_time = realtime_info.get("query_time", "未知")
        nav_val = realtime_info.get("latest_nav")
        nav_date = realtime_info.get("nav_date")
        day_growth = realtime_info.get("day_growth")

        context += f"### 实时行情（查询时间：{query_time}）\n\n"

        if nav_val and nav_date:
            context += f"- **上一交易日收盘净值**：{nav_val:.4f}（日期：{nav_date}）\n"

        if day_growth is not None:
            context += f"- **今日盘中实时估值涨跌幅**：{day_growth:+.2f}%（这是今天交易时段的实时估算，非收盘确认值）\n"
            if nav_val:
                est_nav = nav_val * (1 + day_growth / 100)
                context += f"- **今日估算净值**：{est_nav:.4f}（= 上一交易日净值 {nav_val:.4f} x (1 + {day_growth:+.2f}%)）\n"

        context += "\n"

    context += f"### 近 {len(nav_data)} 个交易日历史净值数据\n\n"
    context += "以下数据为已确认的每日收盘净值（非实时估值）：\n\n"
    context += "| 日期 | 单位净值 | 累计净值 | 日涨跌% |\n"
    context += "|------|----------|----------|--------|\n"

    for row in nav_data:
        nav_date = row.get("日期", "-")
        nav_val = row.get("单位净值", "-")
        acc_nav = row.get("累计净值", "-")
        daily_ret = row.get("日涨跌%", "-")

        if daily_ret and daily_ret != "-" and daily_ret is not None:
            daily_ret_str = f"{daily_ret:+.2f}%" if isinstance(daily_ret, (int, float)) else str(daily_ret)
        else:
            daily_ret_str = "-"

        acc_nav_str = f"{acc_nav:.4f}" if isinstance(acc_nav, (int, float)) and acc_nav else "-"
        nav_str = f"{nav_val:.4f}" if isinstance(nav_val, (int, float)) else str(nav_val)

        context += f"| {nav_date} | {nav_str} | {acc_nav_str} | {daily_ret_str} |\n"

    # 计算基础统计
    navs = [row["单位净值"] for row in nav_data if row.get("单位净值") and isinstance(row["单位净值"], (int, float))]
    if len(navs) >= 2:
        latest = navs[0]
        earliest = navs[-1]
        period_return = (latest - earliest) / earliest * 100
        max_nav = max(navs)
        min_nav = min(navs)
        max_drawdown = (max_nav - min_nav) / max_nav * 100 if max_nav > 0 else 0

        context += f"\n**区间统计**：\n"
        context += f"- 最新净值：{latest:.4f}\n"
        context += f"- 区间涨跌：{period_return:+.2f}%\n"
        context += f"- 区间最高：{max_nav:.4f}\n"
        context += f"- 区间最低：{min_nav:.4f}\n"
        context += f"- 区间最大回撤：{max_drawdown:.2f}%\n"

    return context


def chat_with_nav_context(
    messages: list[dict],
    nav_context: str,
    system_prompt: str,
    temperature: float = 0.7,
) -> LLMResponse:
    """
    基于净值数据上下文进行多轮对话

    参数:
        messages: 对话历史 [{"role": "user"/"assistant", "content": "..."}]
        nav_context: 净值数据上下文文本（由 build_nav_context 生成）
        system_prompt: 角色系统提示词
        temperature: 生成温度

    返回:
        LLMResponse 对象
    """
    client = get_llm_client()
    if not client:
        return LLMResponse(
            success=False,
            content="",
            error="LLM 未配置，请在【系统设置 → LLM配置】中设置 API 地址、密钥和模型",
        )

    # 构建完整的系统提示词，注入净值数据上下文
    full_system_prompt = f"""{system_prompt}

---

## 当前数据上下文

{nav_context}

---

请基于以上数据回答用户的问题。如果用户的问题与提供的数据无关，可以基于你的金融知识回答，但需要说明是通用分析而非针对具体数据。"""

    # 组装消息列表
    api_messages = [{"role": "system", "content": full_system_prompt}]
    api_messages.extend(messages)

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=2000,
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
            error=f"AI 对话失败：{str(e)}",
        )


# ============ 会话管理 ============

def create_session(
    db: Session,
    title: str,
    fund_code: str = "",
    fund_name: str = "",
    role_name: str = "",
) -> ChatSession:
    """创建新的对话会话"""
    session = ChatSession(
        title=title,
        fund_code=fund_code or None,
        fund_name=fund_name or None,
        role_name=role_name,
    )
    db.add(session)
    db.flush()
    return session


def get_session_by_id(db: Session, session_id: int) -> Optional[ChatSession]:
    """根据ID获取会话（含消息）"""
    return db.query(ChatSession).filter(ChatSession.id == session_id).first()


def get_recent_sessions(db: Session, limit: int = 20) -> list[ChatSession]:
    """获取最近的对话会话列表"""
    return (
        db.query(ChatSession)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
        .all()
    )


def delete_session(db: Session, session_id: int) -> bool:
    """删除对话会话（级联删除消息）"""
    session = get_session_by_id(db, session_id)
    if not session:
        return False
    db.delete(session)
    db.flush()
    return True


def add_message(
    db: Session,
    session_id: int,
    role: str,
    content: str,
) -> ChatMessage:
    """向会话添加一条消息"""
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
    )
    db.add(message)

    # 更新会话的消息计数和活跃时间
    session = get_session_by_id(db, session_id)
    if session:
        session.message_count = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .count()
            + 1
        )

    db.flush()
    return message


def get_session_messages(db: Session, session_id: int) -> list[dict]:
    """获取会话的所有消息，返回 [{"role": ..., "content": ...}] 格式"""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in messages]


def export_session_markdown(db: Session, session_id: int) -> Optional[str]:
    """将会话导出为 Markdown 格式文本"""
    session = get_session_by_id(db, session_id)
    if not session:
        return None

    lines = []
    lines.append(f"# {session.title}")
    lines.append("")
    if session.fund_name and session.fund_code:
        lines.append(f"**基金**：{session.fund_name}（{session.fund_code}）")
    lines.append(f"**角色**：{session.role_name}")
    lines.append(f"**时间**：{session.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**消息数**：{session.message_count}")
    lines.append("")
    lines.append("---")
    lines.append("")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    for msg in messages:
        time_str = msg.created_at.strftime("%H:%M")
        if msg.role == "user":
            lines.append(f"### 用户 ({time_str})")
        else:
            lines.append(f"### AI ({time_str})")
        lines.append("")
        lines.append(msg.content)
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("> 以上对话内容仅供研究参考，不构成投资建议。")
    return "\n".join(lines)
