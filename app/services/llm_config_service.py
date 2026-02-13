"""
LLM 配置管理服务

支持动态配置 LLM API，获取可用模型列表，保存/加载配置。
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from openai import OpenAI


# 配置文件路径
CONFIG_DIR = Path(__file__).resolve().parents[2] / "data"
CONFIG_FILE = CONFIG_DIR / "llm_config.json"


@dataclass
class LLMConfig:
    """LLM 配置"""
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    available_models: list[str] = None

    def __post_init__(self):
        if self.available_models is None:
            self.available_models = []


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    owned_by: str = ""
    created: int = 0


def ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> LLMConfig:
    """
    加载 LLM 配置

    优先从配置文件加载，如果没有则从环境变量读取
    """
    import os

    # 尝试从配置文件加载
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return LLMConfig(
                    base_url=data.get("base_url", ""),
                    api_key=data.get("api_key", ""),
                    model=data.get("model", ""),
                    available_models=data.get("available_models", []),
                )
        except Exception:
            pass

    # 从环境变量读取（兼容旧配置）
    return LLMConfig(
        base_url=os.getenv("LLM_BASE_URL", ""),
        api_key=os.getenv("LLM_API_KEY", ""),
        model=os.getenv("LLM_MODEL", ""),
        available_models=[],
    )


def save_config(config: LLMConfig) -> bool:
    """
    保存 LLM 配置到文件

    返回:
        是否保存成功
    """
    try:
        ensure_config_dir()
        data = {
            "base_url": config.base_url,
            "api_key": config.api_key,
            "model": config.model,
            "available_models": config.available_models,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False


def fetch_available_models(base_url: str, api_key: str) -> tuple[list[ModelInfo], Optional[str]]:
    """
    从 API 获取可用模型列表

    参数:
        base_url: API 基础地址
        api_key: API 密钥

    返回:
        (模型列表, 错误信息)
    """
    if not base_url or not api_key:
        return [], "请先填写 API 地址和密钥"

    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=30.0,
        )

        # 调用 /v1/models 接口
        response = client.models.list()

        models = []
        for model in response.data:
            models.append(ModelInfo(
                id=model.id,
                owned_by=getattr(model, "owned_by", ""),
                created=getattr(model, "created", 0),
            ))

        # 按模型ID排序
        models.sort(key=lambda m: m.id)

        return models, None

    except Exception as e:
        error_msg = str(e)
        # 简化错误信息
        if "Connection" in error_msg:
            return [], f"连接失败：请检查 API 地址是否正确"
        elif "401" in error_msg or "Unauthorized" in error_msg:
            return [], "认证失败：请检查 API 密钥是否正确"
        elif "404" in error_msg:
            return [], "接口不存在：该 API 可能不支持 /v1/models 接口"
        else:
            return [], f"获取模型列表失败：{error_msg}"


def test_connection(base_url: str, api_key: str, model: str) -> tuple[bool, str]:
    """
    测试 LLM 连接

    参数:
        base_url: API 基础地址
        api_key: API 密钥
        model: 模型名称

    返回:
        (是否成功, 消息)
    """
    if not base_url or not api_key or not model:
        return False, "请填写完整的配置信息"

    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=30.0,
        )

        # 发送简单的测试请求
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "你好，请回复「连接成功」"}
            ],
            max_tokens=50,
        )

        content = response.choices[0].message.content
        return True, f"连接成功！模型响应：{content[:50]}..."

    except Exception as e:
        error_msg = str(e)
        if "Connection" in error_msg:
            return False, "连接失败：请检查 API 地址"
        elif "401" in error_msg or "Unauthorized" in error_msg:
            return False, "认证失败：请检查 API 密钥"
        elif "model" in error_msg.lower():
            return False, f"模型不可用：{model}"
        else:
            return False, f"测试失败：{error_msg[:100]}"


# 全局配置实例（用于运行时访问）
_current_config: Optional[LLMConfig] = None


def get_current_config() -> LLMConfig:
    """获取当前配置（带缓存）"""
    global _current_config
    if _current_config is None:
        _current_config = load_config()
    return _current_config


def update_current_config(config: LLMConfig):
    """更新当前配置缓存"""
    global _current_config
    _current_config = config


def reload_config():
    """重新加载配置"""
    global _current_config
    _current_config = load_config()
    return _current_config
