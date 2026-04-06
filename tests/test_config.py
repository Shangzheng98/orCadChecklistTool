"""Tests for Oracle configuration and JDBC/YAML parsing."""
import pytest
from pathlib import Path

from orcad_checker.store.config import OracleConfig


# ── JDBC URL 解析 ────────────────────────────────────────────

def test_parse_jdbc_url_with_sid():
    config = OracleConfig.from_jdbc_url(
        jdbc_url="jdbc:oracle:thin:@dbhost:1521:ORCL",
        user="testuser",
        password="testpass",
    )
    assert config.host == "dbhost"
    assert config.port == 1521
    assert config.sid == "ORCL"
    assert config.service_name is None
    assert config.user == "testuser"
    assert config.password == "testpass"


def test_parse_jdbc_url_with_service_name():
    config = OracleConfig.from_jdbc_url(
        jdbc_url="jdbc:oracle:thin:@dbhost:1521/orcl_service",
        user="u",
        password="p",
    )
    assert config.host == "dbhost"
    assert config.port == 1521
    assert config.sid is None
    assert config.service_name == "orcl_service"


def test_parse_jdbc_url_invalid():
    with pytest.raises(ValueError, match="Invalid JDBC URL"):
        OracleConfig.from_jdbc_url(
            jdbc_url="not-a-jdbc-url",
            user="u",
            password="p",
        )


def test_pool_defaults():
    config = OracleConfig.from_jdbc_url(
        jdbc_url="jdbc:oracle:thin:@h:1521:SID",
        user="u",
        password="p",
    )
    assert config.pool_min == 2
    assert config.pool_max == 10


def test_pool_override():
    config = OracleConfig.from_jdbc_url(
        jdbc_url="jdbc:oracle:thin:@h:1521:SID",
        user="u",
        password="p",
        pool_min=5,
        pool_max=20,
    )
    assert config.pool_min == 5
    assert config.pool_max == 20


def test_make_dsn_with_sid():
    config = OracleConfig.from_jdbc_url(
        jdbc_url="jdbc:oracle:thin:@dbhost:1521:ORCL",
        user="u",
        password="p",
    )
    dsn = config.make_dsn()
    assert "dbhost" in dsn
    assert "1521" in dsn


# ── YAML 配置文件加载 ───────────────────────────────────────

def test_from_yaml_with_sid(tmp_path):
    """从 YAML 文件加载 SID 格式配置。"""
    config_file = tmp_path / "database.yaml"
    config_file.write_text("""
oracle:
  jdbc_url: "jdbc:oracle:thin:@yamlhost:1521:YAMLSID"
  user: "yamluser"
  password: "yamlpass"
  pool_min: 3
  pool_max: 15
""")
    config = OracleConfig.from_yaml(config_file)
    assert config.host == "yamlhost"
    assert config.port == 1521
    assert config.sid == "YAMLSID"
    assert config.user == "yamluser"
    assert config.password == "yamlpass"
    assert config.pool_min == 3
    assert config.pool_max == 15


def test_from_yaml_with_service_name(tmp_path):
    """从 YAML 文件加载 Service Name 格式配置。"""
    config_file = tmp_path / "database.yaml"
    config_file.write_text("""
oracle:
  jdbc_url: "jdbc:oracle:thin:@svchost:1522/my_service"
  user: "u"
  password: "p"
""")
    config = OracleConfig.from_yaml(config_file)
    assert config.host == "svchost"
    assert config.port == 1522
    assert config.sid is None
    assert config.service_name == "my_service"


def test_from_yaml_pool_defaults(tmp_path):
    """YAML 中不指定连接池参数时使用默认值。"""
    config_file = tmp_path / "database.yaml"
    config_file.write_text("""
oracle:
  jdbc_url: "jdbc:oracle:thin:@h:1521:SID"
  user: "u"
  password: "p"
""")
    config = OracleConfig.from_yaml(config_file)
    assert config.pool_min == 2
    assert config.pool_max == 10


def test_from_yaml_file_not_found():
    """配置文件不存在时抛出 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        OracleConfig.from_yaml("/nonexistent/database.yaml")


def test_from_yaml_missing_oracle_section(tmp_path):
    """YAML 中缺少 oracle 节时抛出 ValueError。"""
    config_file = tmp_path / "database.yaml"
    config_file.write_text("something_else: true\n")
    with pytest.raises(ValueError, match="oracle"):
        OracleConfig.from_yaml(config_file)


def test_from_yaml_missing_jdbc_url(tmp_path):
    """YAML 中缺少 jdbc_url 时抛出 ValueError。"""
    config_file = tmp_path / "database.yaml"
    config_file.write_text("""
oracle:
  user: "u"
  password: "p"
""")
    with pytest.raises(ValueError, match="jdbc_url"):
        OracleConfig.from_yaml(config_file)
