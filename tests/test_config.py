"""Tests for Oracle configuration and JDBC URL parsing."""
import os
import pytest
from orcad_checker.store.config import OracleConfig


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


def test_from_env(monkeypatch):
    monkeypatch.setenv("ORACLE_JDBC_URL", "jdbc:oracle:thin:@envhost:1522:ENVSID")
    monkeypatch.setenv("ORACLE_USER", "envuser")
    monkeypatch.setenv("ORACLE_PASSWORD", "envpass")
    monkeypatch.setenv("ORACLE_POOL_MIN", "3")
    monkeypatch.setenv("ORACLE_POOL_MAX", "15")

    config = OracleConfig.from_env()
    assert config.host == "envhost"
    assert config.port == 1522
    assert config.sid == "ENVSID"
    assert config.user == "envuser"
    assert config.password == "envpass"
    assert config.pool_min == 3
    assert config.pool_max == 15


def test_from_env_missing_url(monkeypatch):
    monkeypatch.delenv("ORACLE_JDBC_URL", raising=False)
    with pytest.raises(ValueError, match="ORACLE_JDBC_URL"):
        OracleConfig.from_env()
