"""OpenAPI / Swagger 文档解析（可选发现路径）。"""
from __future__ import annotations

import re
from typing import Any

import httpx

from ..config import DiscoverySettings
from ..models import FunctionalPoint


OPENAPI_PATHS = (
    "/openapi.json",
    "/swagger.json",
    "/v3/api-docs",
    "/v2/api-docs",
    "/api-docs",
    "/docs/openapi.json",
)

SAFE_METHODS = {"get", "head", "options"}


def _resolve_ref(spec: dict, ref: str) -> dict:
    if not ref.startswith("#/"):
        return {}
    node: Any = spec
    for part in ref[2:].split("/"):
        if isinstance(node, dict):
            node = node.get(part, {})
        else:
            return {}
    return node if isinstance(node, dict) else {}


def parse_openapi(spec: dict[str, Any], base_url: str) -> list[FunctionalPoint]:
    from urllib.parse import urljoin

    points: list[FunctionalPoint] = []
    paths = spec.get("paths") or {}
    for path, ops in paths.items():
        if not isinstance(ops, dict):
            continue
        for method, op in ops.items():
            if method.lower() not in SAFE_METHODS:
                continue
            if not isinstance(op, dict):
                continue
            params = []
            for p in op.get("parameters") or []:
                if isinstance(p, dict) and "$ref" in p:
                    p = _resolve_ref(spec, p["$ref"])
                if not isinstance(p, dict):
                    continue
                params.append(
                    {
                        "name": p.get("name", ""),
                        "in": p.get("in", "query"),
                        "required": p.get("required", False),
                        "description": p.get("description", ""),
                        "schema": p.get("schema", {}),
                    }
                )
            tags = list(op.get("tags") or [])
            tags.append("openapi")
            # 简单路径参数提示
            path_params = re.findall(r"\{(\w+)\}", path)
            for name in path_params:
                if not any(p.get("name") == name for p in params):
                    params.append({"name": name, "in": "path", "required": True})

            full = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
            points.append(
                FunctionalPoint(
                    id="",
                    name=op.get("summary") or op.get("operationId") or path,
                    method=method.upper(),
                    url=full,
                    path=path,
                    source="swagger",
                    summary=op.get("description") or op.get("summary") or "",
                    params=params,
                    tags=tags,
                    response_hints=", ".join(
                        (op.get("responses") or {}).keys()
                    ),
                )
            )
    return points


def try_fetch_openapi(
    base_url: str,
    client: httpx.Client,
    settings: DiscoverySettings,
) -> tuple[list[FunctionalPoint], list[str]]:
    warnings: list[str] = []
    from urllib.parse import urljoin

    for p in OPENAPI_PATHS:
        url = urljoin(base_url.rstrip("/") + "/", p.lstrip("/"))
        try:
            r = client.get(url, timeout=min(settings.timeout, 10))
            if r.status_code != 200:
                continue
            data = r.json()
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if "openapi" in data or "swagger" in data or "paths" in data:
            pts = parse_openapi(data, base_url)
            if pts:
                warnings.append(f"已从 OpenAPI 文档发现 {len(pts)} 个查询接口: {p}")
                return pts, warnings
    return [], warnings
