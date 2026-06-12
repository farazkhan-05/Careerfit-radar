from __future__ import annotations

from pathlib import Path


FRONTEND_ROOT = Path(__file__).parent.parent / "frontend"


def test_frontend_package_json_exists() -> None:
    assert (FRONTEND_ROOT / "package.json").exists(), "frontend/package.json must exist"


def test_frontend_env_example_exists() -> None:
    assert (FRONTEND_ROOT / ".env.example").exists(), "frontend/.env.example must exist"


def test_frontend_env_example_defines_api_url() -> None:
    content = (FRONTEND_ROOT / ".env.example").read_text()
    assert "VITE_API_URL" in content, ".env.example must define VITE_API_URL"


def test_frontend_vite_config_exists() -> None:
    assert (FRONTEND_ROOT / "vite.config.js").exists(), "frontend/vite.config.js must exist"


def test_frontend_vite_proxy_forwards_backend_auth_token() -> None:
    content = (FRONTEND_ROOT / "vite.config.js").read_text()

    assert "loadEnv" in content, "Vite config must load root env for dev proxy settings"
    assert "API_AUTH_TOKEN" in content, "Vite proxy must read backend API_AUTH_TOKEN"
    assert "setHeader('Authorization'" in content, "Vite proxy must forward auth to backend"


def test_frontend_src_entry_exists() -> None:
    assert (FRONTEND_ROOT / "src" / "main.jsx").exists(), "frontend/src/main.jsx must exist"


def test_frontend_api_client_uses_env_var() -> None:
    client_path = FRONTEND_ROOT / "src" / "api" / "client.js"
    assert client_path.exists(), "frontend/src/api/client.js must exist"
    content = client_path.read_text()
    assert "VITE_API_URL" in content, "API client must read base URL from VITE_API_URL"


def test_no_hardcoded_localhost_in_api_client() -> None:
    client_path = FRONTEND_ROOT / "src" / "api" / "client.js"
    content = client_path.read_text()
    # Localhost is only allowed as the fallback default, not the primary source
    lines_with_localhost = [line for line in content.splitlines() if "localhost" in line and "VITE_API_URL" not in line]
    assert len(lines_with_localhost) <= 1, (
        "API client should only reference localhost as a fallback default alongside VITE_API_URL"
    )


def test_backend_cors_setting_exists() -> None:
    backend_config = Path(__file__).parent.parent / "backend" / "config.py"
    content = backend_config.read_text()
    assert "cors_origins" in content, "backend/config.py must define cors_origins setting"


def test_backend_main_has_cors_middleware() -> None:
    main_path = Path(__file__).parent.parent / "backend" / "main.py"
    content = main_path.read_text()
    assert "CORSMiddleware" in content, "backend/main.py must configure CORSMiddleware"


def test_frontend_container_renders_nginx_template_at_runtime() -> None:
    dockerfile = (Path(__file__).parent.parent / "Dockerfile.frontend").read_text()
    entrypoint = FRONTEND_ROOT / "docker-entrypoint.sh"
    entrypoint_content = entrypoint.read_text()
    nginx_template = (FRONTEND_ROOT / "nginx.conf").read_text()

    assert entrypoint.exists(), "frontend container must include a runtime entrypoint"
    assert "envsubst" in entrypoint_content, "entrypoint must render nginx template env vars"
    assert "nginx -t" in entrypoint_content, "entrypoint must validate nginx config"
    assert "nginx -T" not in entrypoint_content, "entrypoint must not log secrets in active nginx config"
    assert "proxy_ssl_server_name on" in nginx_template, "Cloud Run upstream TLS must use backend SNI"
    assert "proxy_set_header Host $proxy_host" in nginx_template, "Cloud Run upstream Host must target backend"
    assert "proxy_set_header X-Forwarded-Host $host" in nginx_template
    assert "ENTRYPOINT" in dockerfile, "Dockerfile.frontend must use the custom entrypoint"
    assert "/docker-entrypoint-careerfit.sh" in dockerfile
