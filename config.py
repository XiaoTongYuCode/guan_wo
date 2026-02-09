"""
应用程序配置
"""
# 标准库导包
from typing import List, Dict, Any

# 第三方库导包
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用程序设置类"""
    
    # 应用基本信息
    APP_NAME: str = "GUAN WO"
    APP_VERSION: str = "1.0.0"
    POD_ENV: str = Field(default="test", env="POD_ENV")
    DEBUG: bool = Field(default_factory=lambda: Settings._get_debug())
    RELOAD: bool = False
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = 1
    
    # 开发环境数据库配置
    DEV_DB_HOST: str = "localhost:3306"
    DEV_DB_USER: str = "root"
    DEV_DB_PASSWORD: str = "12345678"
    
    # 线上环境数据库配置
    ONLINE_DB_HOST: str = "localhost:3306"
    ONLINE_DB_USER: str = "root"
    ONLINE_DB_PASSWORD: str = "12345678"
    
    REDIS_DEV_URL: str = "redis://localhost:6379/0"
    REDIS_YUFA_URL: str =  "redis://localhost:6379/0"
    REDIS_ONLINE_URL: str =  "redis://localhost:6379/0"
    # 数据库名称
    DB_NAME: str = "guanwo_db"
    
    # 数据库连接池配置
    DB_POOL_SIZE: int = Field(default=10, env="DB_POOL_SIZE")
    DB_MAX_CONNECTIONS: int = Field(default=20, env="DB_MAX_CONNECTIONS")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=3600, env="DB_POOL_RECYCLE")
    
    # 阿里云配置
    ALIYUN_ACCESS_KEY_ID: str = Field(default="your-aliyun-ak-id", env="ALIYUN_ACCESS_KEY_ID")
    ALIYUN_ACCESS_KEY_SECRET: str = Field(default="your-aliyun-ak-secret", env="ALIYUN_ACCESS_KEY_SECRET")
    ALIYUN_REGION: str = Field(default="cn-shanghai", env="ALIYUN_REGION")
    ALIYUN_ASR_APP_KEY: str = Field(default="your-asr-app-key", env="ALIYUN_ASR_APP_KEY")
    ALIYUN_ASR_ENDPOINT: str = Field(default="http://nls-gateway.cn-shanghai.aliyuncs.com", env="ALIYUN_ASR_ENDPOINT")
    ALIYUN_GREEN_ENDPOINT: str = Field(default="green-cip.cn-shanghai.aliyuncs.com", env="ALIYUN_GREEN_ENDPOINT")
    
    # CORS配置 - 允许所有跨域请求
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # 日志配置
    LOG_LEVEL: str = Field(default="info", env="LOG_LEVEL")
    
    # Redis会话配置
    WORKFLOW_SESSION_TTL: int = 3600 * 24 * 30  # 会话TTL（30天）
    
    # LLM配置
    LLM_PROVIDERS: Dict[str, Any] = Field(
        default={
            "siliconflow": {
                "api_key": "sk-aheanfzzxekditiebmtlskyekdxuzgamhdxoajhgagbzoere",
                "base_url": "https://api.siliconflow.cn/v1",
                "models": {
                    "kimi-k2": {
                        "id": "moonshotai/Kimi-K2-Instruct",
                        "name": "Kimi K2"
                    }
                }
            },
            "ark": {
                "api_key": "7fb7a28d-f55d-41b7-82c1-e09ef5b8015c",
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "models": {
                    "doubao-seed-1-6-flash": {
                        "id": "doubao-seed-1-6-flash-250715",
                        "name": "Doubao Seed 1.6 Flash 250715"
                    }
                }
            }
        },
        description="LLM提供商配置"
    )
    DEFAULT_LLM_PROVIDER: str = Field(default="siliconflow", description="默认LLM提供商")
    DEFAULT_LLM_MODEL_KEY: str = Field(default="kimi-k2", description="默认LLM模型键")
    
    @property
    def REDIS_KEY_PREFIXES(self) -> dict:
        """Redis key前缀常量"""
        return {
            "CHAT_SESSION": "tyc_universal_search_us:chat_session:",
            "USER_SESSIONS": "tyc_universal_search_us:user_sessions:",
        }
    
    @staticmethod
    def _get_debug() -> bool:
        """获取DEBUG模式，基于POD_ENV环境变量"""
        import os
        return os.getenv("POD_ENV", "test").lower() != "online"
    
    # 根据环境变量设置当前数据库配置
    @property
    def DB_HOST(self) -> str:
        if self.POD_ENV == "online":
            return self.ONLINE_DB_HOST
        else:  # 默认使用开发环境
            return self.DEV_DB_HOST
    
    @property
    def DB_USER(self) -> str:
        if self.POD_ENV == "online":
            return self.ONLINE_DB_USER
        else:
            return self.DEV_DB_USER
    
    @property
    def DB_PASSWORD(self) -> str:
        if self.POD_ENV == "online":
            return self.ONLINE_DB_PASSWORD
        else:
            return self.DEV_DB_PASSWORD
    
    @property
    def REDIS_URL(self) -> str:
        """根据环境返回对应的Redis连接URL"""
        if self.POD_ENV == "online":
            return self.REDIS_ONLINE_URL
        elif self.POD_ENV == "yufa":
            return self.REDIS_YUFA_URL
        else:  # 默认使用开发环境
            return self.REDIS_DEV_URL
                
    
    # API文档配置
    @property
    def DOCS_URL(self) -> str:
        return "/docs" if self.DEBUG else None
    
    @property
    def REDOC_URL(self) -> str:
        return "/redoc" if self.DEBUG else None
    
    @property
    def OPENAPI_URL(self) -> str:
        return "/openapi.json" if self.DEBUG else None

    class Config:
        """Pydantic配置"""
        env_file = ".env"  # 支持从.env文件读取配置
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建设置实例
settings = Settings() 