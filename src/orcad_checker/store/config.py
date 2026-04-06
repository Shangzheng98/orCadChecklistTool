"""Oracle 数据库连接配置。

从 YAML 配置文件解析 Oracle 连接参数。

配置文件默认路径: config/database.yaml

YAML 格式:
    oracle:
      jdbc_url: "jdbc:oracle:thin:@host:port:SID"
      user: "username"
      password: "password"
      pool_min: 2
      pool_max: 10

支持两种 JDBC URL 格式:
    - SID 格式:          jdbc:oracle:thin:@host:port:SID
    - Service Name 格式: jdbc:oracle:thin:@host:port/service_name
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import oracledb
import yaml

# 默认配置文件路径 (项目根目录下 config/database.yaml)
_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "database.yaml"


@dataclass
class OracleConfig:
    """Oracle 连接配置。

    Attributes:
        host:         数据库主机地址。
        port:         监听端口。
        sid:          Oracle SID (与 service_name 二选一)。
        service_name: Oracle Service Name (与 sid 二选一)。
        user:         数据库用户名。
        password:     数据库密码。
        pool_min:     连接池最小连接数。
        pool_max:     连接池最大连接数。
    """
    host: str
    port: int
    user: str
    password: str
    sid: str | None = None
    service_name: str | None = None
    pool_min: int = 2
    pool_max: int = 10

    def make_dsn(self) -> str:
        """构造 oracledb DSN 连接串。"""
        if self.sid:
            return oracledb.makedsn(self.host, self.port, sid=self.sid)
        return oracledb.makedsn(self.host, self.port, service_name=self.service_name)

    @classmethod
    def from_jdbc_url(
        cls,
        jdbc_url: str,
        user: str,
        password: str,
        pool_min: int = 2,
        pool_max: int = 10,
    ) -> OracleConfig:
        """从 JDBC URL 解析配置。

        支持格式:
            jdbc:oracle:thin:@host:port:SID
            jdbc:oracle:thin:@host:port/service_name

        Raises:
            ValueError: JDBC URL 格式无效。
        """
        # 匹配 SID 格式: @host:port:SID
        sid_match = re.search(r'@([\w.\-]+):(\d+):(\w+)$', jdbc_url)
        if sid_match:
            return cls(
                host=sid_match.group(1),
                port=int(sid_match.group(2)),
                sid=sid_match.group(3),
                service_name=None,
                user=user,
                password=password,
                pool_min=pool_min,
                pool_max=pool_max,
            )

        # 匹配 Service Name 格式: @host:port/service_name
        svc_match = re.search(r'@([\w.\-]+):(\d+)/([\w.\-]+)$', jdbc_url)
        if svc_match:
            return cls(
                host=svc_match.group(1),
                port=int(svc_match.group(2)),
                sid=None,
                service_name=svc_match.group(3),
                user=user,
                password=password,
                pool_min=pool_min,
                pool_max=pool_max,
            )

        raise ValueError(
            f"Invalid JDBC URL format: {jdbc_url}. "
            "Expected: jdbc:oracle:thin:@host:port:SID or jdbc:oracle:thin:@host:port/service_name"
        )

    @classmethod
    def from_yaml(cls, config_path: str | Path | None = None) -> OracleConfig:
        """从 YAML 配置文件加载配置。

        Args:
            config_path: YAML 文件路径。为 None 时使用默认路径 config/database.yaml。

        Raises:
            FileNotFoundError: 配置文件不存在。
            ValueError: 配置文件缺少必需字段。
        """
        path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH

        if not path.exists():
            raise FileNotFoundError(f"数据库配置文件不存在: {path}")

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        oracle = data.get("oracle")
        if not oracle:
            raise ValueError(f"配置文件缺少 'oracle' 节: {path}")

        jdbc_url = oracle.get("jdbc_url")
        if not jdbc_url:
            raise ValueError(f"配置文件缺少 'oracle.jdbc_url': {path}")

        user = oracle.get("user", "")
        password = oracle.get("password", "")
        pool_min = int(oracle.get("pool_min", 2))
        pool_max = int(oracle.get("pool_max", 10))

        return cls.from_jdbc_url(
            jdbc_url=jdbc_url,
            user=user,
            password=password,
            pool_min=pool_min,
            pool_max=pool_max,
        )
