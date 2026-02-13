import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


@dataclass
class Settings:
    """应用配置"""
    app_name: str = os.getenv("APP_NAME", "AI基金分析助手")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    ui_port: int = int(os.getenv("UI_PORT", "8501"))
    sqlite_path: Path = BASE_DIR / "data" / "app.db"

    # LLM 配置（运行时动态获取）
    _llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    _llm_api_key: str = os.getenv("LLM_API_KEY", "")
    _llm_model: str = os.getenv("LLM_MODEL", "")

    @property
    def database_url(self) -> str:
        override = os.getenv("DATABASE_URL", "")
        if override:
            return override
        return f"sqlite:///{self.sqlite_path.as_posix()}"

    @property
    def llm_base_url(self) -> str:
        """获取 LLM API 地址（优先从配置文件读取）"""
        from app.services.llm_config_service import get_current_config
        config = get_current_config()
        return config.base_url if config.base_url else self._llm_base_url

    @property
    def llm_api_key(self) -> str:
        """获取 LLM API 密钥（优先从配置文件读取）"""
        from app.services.llm_config_service import get_current_config
        config = get_current_config()
        return config.api_key if config.api_key else self._llm_api_key

    @property
    def llm_model(self) -> str:
        """获取 LLM 模型名称（优先从配置文件读取）"""
        from app.services.llm_config_service import get_current_config
        config = get_current_config()
        return config.model if config.model else self._llm_model


settings = Settings()

