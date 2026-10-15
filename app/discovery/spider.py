"""只读功能点发现：抓取页面链接 + 识别查询类 API。"""
from __future__ import annotations

import re
import uuid
from collections import deque
from html import unescape
from typing import Any
from urllib.parse import parse_qsl, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from ..auth import AuthConfig, build_headers, path_is_denied
from ..config import DiscoverySettings
from ..models import FunctionalPoint


API_HINT_RE = re.compile(
    r"""(?P<u>(?:https?:)?//[^"'\\s]+|(?:/[\w\-.~%]+){1,8}(?:\?[^"'\\s]*)?)""",
    re.I,
)
# JS 里常见 fetch/axios 调用
FETCH_RE = re.compile(
    r"""(?:fetch|axios\.(?:get|request)|\$\.(?:get|ajax))\s*\(\s*['"`](?P<u>[^'"`]+)['"`]""",
    re.I,
)
HREF_RE = re.compile(r"""(?:href|action|src)\s*=\s*['"](?P<u>[^'"]+)['"]""", re.I)


def _normalize_url(base: str, href: str) -> str | None:
    if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
        return None
    href = unescape(href.strip())
    try:
        absu = urljoin(base, href)
        parsed = urlparse(absu)
        if parsed.scheme not in ("http", "https"):
            return None
        # 去掉 fragment
        cleaned = parsed._replace(fragment="")
        return urlunparse(cleaned)
    except Exception:
        return None


def _same_origin(a: str, b: str) -> bool:
    pa, pb = urlparse(a), urlparse(b)
    return (pa.scheme, pa.netloc) == (pb.scheme, pb.netloc)


def _looks_like_api(url: str, hints: list[str]) -> bool:
    path = urlparse(url).path.lower()
    return any(h.lower() in path for h in hints)


def _extract_params_from_url(url: str) -> list[dict[str, Any]]:
    qs = parse_qsl(urlparse(url).query, keep_blank_values=True)
    return [{"name": k, "in": "query", "example": v} for k, v in qs]


def _page_name(soup: BeautifulSoup, url: str) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()[:80]
    path = urlparse(url).path.strip("/") or "/"
    return path


def _summarize_page(soup: BeautifulSoup) -> str:
    texts = []
    for sel in ("h1", "h2", "h3", "meta[name=description]", "p"):
        if sel.startswith("meta"):
            m = soup.find("meta", attrs={"name": "description"})
            if m and m.get("content"):
                texts.append(m["content"].strip())
                break
            continue
        for tag in soup.find_all(sel, limit=3):
            t = tag.get_text(" ", strip=True)
            if t:
                texts.append(t)
        if len(" ".join(texts)) > 120:
            break
    return " ".join(texts)[:200]


def discover_functional_points(
    base_url: str,
    auth: AuthConfig,
    settings: DiscoverySettings,
    seed_urls: list[str] | None = None,
) -> tuple[list[FunctionalPoint], list[str], dict[str, Any]]:
    """
    返回 (功能点列表, 警告, 统计)。
    仅做 GET/HEAD 请求，不触发任何写操作。
    """
    warnings: list[str] = []
    headers = build_headers(auth)
    stats: dict[str, Any] = {
        "pages_crawled": 0,
        "links_seen": 0,
        "api_candidates": 0,
        "errors": 0,
    }

    base_url = base_url.strip()
    if not re.match(r"^https?://", base_url, re.I):
        base_url = "https://" + base_url

    points: dict[str, FunctionalPoint] = {}
    seen_urls: set[str] = set()
    queue: deque[tuple[str, int]] = deque()

    seeds = [base_url, *(seed_urls or [])]
    for s in seeds:
        u = _normalize_url(base_url, s) if not s.startswith("http") else s
        if u:
            queue.append((u, 0))
            seen_urls.add(u)

    timeout = httpx.Timeout(settings.timeout)
    try:
        client = httpx.Client(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
            verify=False,  # 测试环境常见自签证书；生产可按需打开
        )
    except Exception as e:
        warnings.append(f"HTTP 客户端初始化失败: {e}")
        return [], warnings, stats

    def add_point(fp: FunctionalPoint) -> None:
        key = f"{fp.method}:{fp.url}"
        if key in points:
            return
        # 路径黑名单
        if path_is_denied(fp.path or fp.url, settings.deny_path_keywords):
            warnings.append(f"[跳过] 疑似写操作路径: {fp.method} {fp.path or fp.url}")
            return
        if not fp.id:
            fp.id = uuid.uuid4().hex[:12]
        points[key] = fp
        if fp.source == "api":
            stats["api_candidates"] += 1

    # 先探测 OpenAPI
    from .swagger import try_fetch_openapi

    openapi_points, oa_warn = try_fetch_openapi(base_url, client, settings)
    warnings.extend(oa_warn)
    for p in openapi_points:
        add_point(p)

    while queue:
        url, depth = queue.popleft()
        if stats["pages_crawled"] >= settings.max_pages:
            warnings.append(f"已达最大抓取页数 {settings.max_pages}，提前结束。")
            break
        if depth > settings.max_depth:
            continue

        method_ok = True
        try:
            resp = client.get(url)
        except Exception as e:
            stats["errors"] += 1
            warnings.append(f"请求失败 {url}: {e}")
            continue

        if resp.status_code >= 400:
            warnings.append(f"HTTP {resp.status_code} @ {url}")
            if resp.status_code in (401, 403):
                warnings.append("鉴权可能失效或权限不足，请检查 Cookie/Token。")
            continue

        ctype = resp.headers.get("content-type", "")
        stats["pages_crawled"] += 1
        parsed = urlparse(url)
        path = parsed.path or "/"

        # JSON 接口
        if "json" in ctype:
            add_point(
                FunctionalPoint(
                    id="",
                    name=path.strip("/").replace("/", ".") or "api-root",
                    method="GET",
                    url=url,
                    path=path,
                    source="api",
                    summary="JSON 查询接口",
                    params=_extract_params_from_url(url),
                    content_type=ctype,
                    tags=["api", "json"],
                    response_hints=str(resp.text)[:300],
                )
            )
            # 尝试从 JSON 里发现更多字段名（不递归爬）
            continue

        if "html" not in ctype and "xml" not in ctype and not ctype:
            # 未知类型，仍记为功能点
            add_point(
                FunctionalPoint(
                    id="",
                    name=path.strip("/") or "resource",
                    method="GET",
                    url=url,
                    path=path,
                    source="page",
                    summary=f"资源: {ctype or 'unknown'}",
                    content_type=ctype,
                    tags=["resource"],
                )
            )
            continue

        html = resp.text
        soup = BeautifulSoup(html, "lxml")
        title = _page_name(soup, url)
        summary = _summarize_page(soup)

        add_point(
            FunctionalPoint(
                id="",
                name=title or path,
                method="GET",
                url=url,
                path=path,
                source="page",
                summary=summary or "页面功能点",
                page_title=title,
                content_type=ctype,
                tags=["page"],
                params=_extract_params_from_url(url),
            )
        )

        # 1) HTML 链接
        for tag in soup.find_all(["a", "form", "link", "script", "iframe"]):
            href = tag.get("href") or tag.get("action") or tag.get("src")
            nu = _normalize_url(url, href)
            if not nu:
                continue
            stats["links_seen"] += 1
            if settings.same_origin_only and not _same_origin(base_url, nu):
                continue
            npath = urlparse(nu).path
            if path_is_denied(npath, settings.deny_path_keywords):
                continue

            if _looks_like_api(nu, settings.include_api_hints) or tag.name == "form":
                # form 仅当 method 缺省/get 时才收录
                if tag.name == "form":
                    fm = (tag.get("method") or "GET").upper()
                    if fm not in settings.allow_methods:
                        warnings.append(f"[跳过] 表单方法 {fm}: {nu}")
                        continue
                add_point(
                    FunctionalPoint(
                        id="",
                        name=npath.strip("/") or urlparse(nu).netloc,
                        method="GET",
                        url=nu,
                        path=npath,
                        source="api" if _looks_like_api(nu, settings.include_api_hints) else "page",
                        summary="页面中发现的查询入口",
                        params=_extract_params_from_url(nu),
                        tags=["linked"],
                    )
                )
            elif depth + 1 <= settings.max_depth and nu not in seen_urls:
                seen_urls.add(nu)
                queue.append((nu, depth + 1))

        # 2) JS 中的 fetch/axios
        for m in FETCH_RE.finditer(html):
            nu = _normalize_url(url, m.group("u"))
            if not nu or (settings.same_origin_only and not _same_origin(base_url, nu)):
                continue
            npath = urlparse(nu).path
            if path_is_denied(npath, settings.deny_path_keywords):
                continue
            add_point(
                FunctionalPoint(
                    id="",
                    name=npath.strip("/") or "js-api",
                    method="GET",
                    url=nu,
                    path=npath,
                    source="api",
                    summary="JS 中发现的接口调用（按 GET 收录）",
                    params=_extract_params_from_url(nu),
                    tags=["js", "api"],
                )
            )

        # 3) 相对 API 线索
        for m in API_HINT_RE.finditer(html):
            raw = m.group("u")
            nu = _normalize_url(url, raw)
            if not nu or (settings.same_origin_only and not _same_origin(base_url, nu)):
                continue
            if not _looks_like_api(nu, settings.include_api_hints):
                continue
            npath = urlparse(nu).path
            if path_is_denied(npath, settings.deny_path_keywords):
                continue
            add_point(
                FunctionalPoint(
                    id="",
                    name=npath.strip("/") or "api",
                    method="GET",
                    url=nu,
                    path=npath,
                    source="api",
                    summary="页面文本中的 API 线索",
                    params=_extract_params_from_url(nu),
                    tags=["hint", "api"],
                )
            )

    client.close()

    # 按 path 去重整理，优先 api
    result = sorted(points.values(), key=lambda p: (p.source != "api", p.path, p.url))
    # 控制总量：页面点优先保留入口
    if len(result) > 80:
        warnings.append(f"功能点较多（{len(result)}），已截取前 80 条供人工筛选。")
        result = result[:80]

    stats["total_points"] = len(result)
    stats["pages_seen"] = len(seen_urls)
    return result, warnings, stats
