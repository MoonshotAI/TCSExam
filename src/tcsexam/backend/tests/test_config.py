"""Config schema tests: defaults, YAML coercion, public_url/auth_enabled.
"""
from __future__ import annotations

import pytest
import yaml

from tcsexam.backend.config import (
    BaseServiceConfig,
    Config,
    JudgeSessionsConfig,
    judge_sessions_from_dict,
    load_config,
)


def test_base_service_config_defaults() -> None:
    config = BaseServiceConfig()
    assert config.public_url() == "http://127.0.0.1:8420"
    assert config.auth_enabled is False


def test_public_base_url_wins_and_strips_slash() -> None:
    config = BaseServiceConfig(public_base_url="https://backend.example.com/")
    assert config.public_url() == "https://backend.example.com"
    assert BaseServiceConfig(token_secret="x").auth_enabled is True


def test_judge_sessions_defaults() -> None:
    cfg = judge_sessions_from_dict({})
    assert cfg == JudgeSessionsConfig()
    assert cfg.command == "python3 /judge/judge_worker.py"
    assert cfg.judge_port == 8082
    assert cfg.work_dir == "/tcsexam-backend"
    assert cfg.gate_session_tokens is False


def test_judge_sessions_partial_override_keeps_defaults() -> None:
    cfg = judge_sessions_from_dict({"max_sessions": "8", "spec": {"cpu_count": 8}})
    assert cfg.max_sessions == 8
    assert cfg.spec["cpu_count"] == 8
    assert cfg.spec["memory_mb"] == 8192  # merged over the defaults
    assert cfg.profile == ""  # untouched (opaque, adapter-defined)


def test_judge_sessions_lifecycle_fields() -> None:
    cfg = judge_sessions_from_dict(
        {
            "failed_retention_seconds": 900,
            "tunnel_reconnect_grace_seconds": 30,
        }
    )
    assert cfg.failed_retention_seconds == 900.0
    assert cfg.tunnel_reconnect_grace_seconds == 30.0
    default = judge_sessions_from_dict({})
    assert default.failed_retention_seconds == 3600.0
    assert default.tunnel_reconnect_grace_seconds == 180.0


def test_judge_sessions_full_coercion() -> None:
    cfg = judge_sessions_from_dict(
        {
            "max_sessions": 4,
            "profile": "cpu-profile",
            "ttl_seconds": 3600,
            "max_ttl_seconds": 7200,
            "ready_timeout_seconds": 60,
            "idle_ttl_seconds": 120,
            "reaper_interval_seconds": 5,
            "work_dir": "/work",
            "command": "",
            "judge_port": 9000,
            "health_path": "/healthz",
            "ready_label": "my-judge",
            "read_timeout_seconds": 60,
            "gate_session_tokens": False,
        }
    )
    assert cfg.command == ""
    assert cfg.judge_port == 9000
    assert cfg.gate_session_tokens is False


def test_judge_sessions_singleflight_default_on() -> None:
    assert judge_sessions_from_dict({}).singleflight is True
    assert JudgeSessionsConfig().singleflight is True
    assert judge_sessions_from_dict({"singleflight": False}).singleflight is False


def test_judge_sessions_routes_parse_and_resolve() -> None:
    cfg = judge_sessions_from_dict(
        {
            "routes": [
                {
                    "match": {"image_contains": "vllm"},
                    "ready_timeout_seconds": 3600,
                    "create_ready_timeout_seconds": 5400,
                },
                {"match": {"image_contains": "knn"}},  # both fields fall back
            ]
        }
    )
    assert cfg.resolve_readiness("registry/vllm-judge:1.0") == (3600.0, 5400.0)
    # A route hit with unset fields: section default + adapter default (None).
    assert cfg.resolve_readiness("registry/knn-judge:1.0") == (cfg.ready_timeout_seconds, None)
    # No route hit: the legacy behavior.
    assert cfg.resolve_readiness("registry/other-judge:1.0") == (1800.0, None)


def test_judge_sessions_routes_first_match_wins() -> None:
    cfg = judge_sessions_from_dict(
        {
            "routes": [
                {"match": {"image_contains": "vllm"}, "ready_timeout_seconds": 111},
                {"match": {"image_contains": "vllm"}, "ready_timeout_seconds": 222},
            ]
        }
    )
    assert cfg.resolve_readiness("registry/vllm-judge:1.0")[0] == 111.0


def test_judge_sessions_routes_invalid_entries_raise() -> None:
    with pytest.raises(ValueError, match="image_contains"):
        judge_sessions_from_dict({"routes": [{"ready_timeout_seconds": 10}]})
    with pytest.raises(ValueError, match="image_contains"):
        judge_sessions_from_dict({"routes": [{"match": {"image_contains": ""}}]})
    with pytest.raises(ValueError, match="positive"):
        judge_sessions_from_dict(
            {"routes": [{"match": {"image_contains": "x"}, "ready_timeout_seconds": 0}]}
        )
    with pytest.raises(ValueError, match="positive"):
        judge_sessions_from_dict(
            {"routes": [{"match": {"image_contains": "x"}, "create_ready_timeout_seconds": -3}]}
        )
    with pytest.raises(ValueError, match="mapping"):
        judge_sessions_from_dict({"routes": ["vllm"]})


def test_public_image_map_defaults_and_loads_from_yaml(tmp_path) -> None:
    assert Config().public_image_map == {}
    path = tmp_path / "config.yaml"
    path.write_text("")
    assert load_config(path).public_image_map == {}

    expected = {
        "registry.example.com/judge:1": "registry.example.com/judge-public-only:1",
    }
    path.write_text(yaml.safe_dump({"public_image_map": expected}))
    assert load_config(path).public_image_map == expected


@pytest.mark.parametrize(
    "mapping",
    [
        [],
        "private-value",
        {"": "registry.example.com/public:1"},
        {"registry.example.com/judge:1": ""},
        {"registry.example.com/judge:1": 42},
        {42: "registry.example.com/public:1"},
        {"registry.example.com/judge:1": "   "},
    ],
)
def test_public_image_map_rejects_invalid_entries_without_echoing_values(
    tmp_path, mapping
) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"public_image_map": mapping}))
    with pytest.raises(ValueError, match="public_image_map") as caught:
        load_config(path)
    assert "private-value" not in str(caught.value)
    assert "registry.example.com" not in str(caught.value)


def test_docker_config_loads_and_accepts_explicit_unlimited_storage(tmp_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({
        "adapter": "docker",
        "docker_socket": "/run/user/1000/docker.sock",
        "docker_network": "tcsexam-net",
        "docker_pull_missing_images": False,
        "docker_host_gateway": False,
        "docker_api_timeout_seconds": 12.5,
        "backend": {"judge_sessions": {"spec": {"storage_mb": None}}},
    }))
    config = load_config(path)
    assert config.adapter == "docker"
    assert config.docker_socket == "/run/user/1000/docker.sock"
    assert config.docker_network == "tcsexam-net"
    assert config.docker_pull_missing_images is False
    assert config.docker_host_gateway is False
    assert config.docker_api_timeout_seconds == 12.5
    assert config.backend.judge_sessions.spec == {
        "cpu_count": 4, "memory_mb": 8192, "storage_mb": None,
    }


def test_docker_socket_environment_override(tmp_path, monkeypatch) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("")
    monkeypatch.setenv("TCSEXAM_DOCKER_SOCKET", "/tmp/tcsexam-docker.sock")
    assert load_config(path).docker_socket == "/tmp/tcsexam-docker.sock"


@pytest.mark.parametrize("socket_path", ["", "relative.sock", "tcp://127.0.0.1:2375", "unix:///var/run/docker.sock"])
def test_docker_config_rejects_non_unix_socket_paths(tmp_path, socket_path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"docker_socket": socket_path}))
    with pytest.raises(ValueError, match="docker_socket"):
        load_config(path)


@pytest.mark.parametrize("field", ["docker_pull_missing_images", "docker_host_gateway"])
def test_docker_config_rejects_non_boolean_switches(tmp_path, field) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({field: "not-a-boolean"}))
    with pytest.raises(ValueError, match="must be booleans"):
        load_config(path)


def test_generated_configuration_requires_all_three_environment_credentials(tmp_path, monkeypatch):
    path=tmp_path/'strict.yaml'
    path.write_text(yaml.safe_dump({'auth':{'require_environment_credentials':True,
        'token_id':'yaml-fallback-id', 'token_secret':'yaml-fallback-secret'},
        'archive_token':'yaml-fallback-archive'}))
    for name in ('TCSEXAM_TOKEN_ID','TCSEXAM_TOKEN_SECRET','TCSEXAM_ARCHIVE_TOKEN'):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match='TCSEXAM_ARCHIVE_TOKEN') as caught:
        load_config(path)
    assert 'yaml-fallback-secret' not in str(caught.value)
    assert 'yaml-fallback-archive' not in str(caught.value)
    monkeypatch.setenv('TCSEXAM_TOKEN_ID','environment-id')
    monkeypatch.setenv('TCSEXAM_TOKEN_SECRET','environment-secret')
    with pytest.raises(ValueError,match='TCSEXAM_ARCHIVE_TOKEN'):
        load_config(path)
    monkeypatch.setenv('TCSEXAM_ARCHIVE_TOKEN','environment-archive')
    config=load_config(path)
    assert config.require_environment_credentials is True
    assert config.token_id=='environment-id'
    assert config.token_secret=='environment-secret'
    assert config.archive_token=='environment-archive'


def test_environment_credential_requirement_rejects_nonboolean_flag(tmp_path):
    path=tmp_path/'bad.yaml'
    path.write_text(yaml.safe_dump({'auth':{'require_environment_credentials':'true'}}))
    with pytest.raises(ValueError,match='must be a boolean'):
        load_config(path)
