"""Oracle 数据库连接配置。

从 JDBC URL 和环境变量解析 Oracle 连接参数。

支持两种 JDBC URL 格式:
    - SID 格式:          jdbc:oracle:thin:@host:port:SID
    - Service Name 格式: jdbc:oracle:thin:@host:port/service_name

环境变量:
    ORACLE_JDBC_URL  - JDBC 连接 URL (必需)
    ORACLE_USER      - 数据库用户名 (必需)
    ORACLE_PASSWORD   - 数据库密码 (必需)
    ORACLE_POOL_MIN  - 连接池最小连接数 (默认: 2)
    ORACLE_POOL_MAX  - 连接池最大连接数 (默认: 10)
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import oracledb


@dataclass
class OracleConfig:
    """Oracle 连接配置。"""
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
        """从 JDBC URL 解析配置。"""
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
    def from_env(cls, prefix: str = "ORACLE_") -> OracleConfig:
        """从环境变量加载配置。"""
        jdbc_url = os.environ.get(f"{prefix}JDBC_URL")
        if not jdbc_url:
            raise ValueError(f"{prefix}JDBC_URL environment variable is required")

        user = os.environ.get(f"{prefix}USER", "")
        password = os.environ.get(f"{prefix}PASSWORD", "")
        pool_min = int(os.environ.get(f"{prefix}POOL_MIN", "2"))
        pool_max = int(os.environ.get(f"{prefix}POOL_MAX", "10"))

        return cls.from_jdbc_url(
            jdbc_url=jdbc_url,
            user=user,
            password=password,
            pool_min=pool_min,
            pool_max=pool_max,
        )
