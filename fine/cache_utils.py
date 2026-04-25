from __future__ import annotations

import hashlib

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import get_token
from django.urls import Resolver404, resolve

CACHE_HEADER = "X-Endpoint-Cache"
_CACHE_KEY_PREFIX = "endpoint-cache"
_CACHE_VERSION_PREFIX = f"{_CACHE_KEY_PREFIX}:version"
_CACHEABLE_METHODS = {"GET", "HEAD"}
_CACHEABLE_STATUS_CODES = {200, 404}


def resolve_route_name(request: HttpRequest) -> str | None:
    if getattr(request, "resolver_match", None) is not None:
        return request.resolver_match.view_name

    try:
        request.resolver_match = resolve(request.path_info)
    except Resolver404:
        return None

    return request.resolver_match.view_name


def get_route_cache_timeout(route_name: str | None) -> int:
    if not route_name:
        return 0
    return int(getattr(settings, "ENDPOINT_CACHE_TIMEOUTS", {}).get(route_name, 0) or 0)


def get_route_cache_namespaces(route_name: str | None) -> tuple[str, ...]:
    if not route_name:
        return ()

    namespaces = {f"route:{route_name}"}
    namespaces.update(getattr(settings, "ENDPOINT_CACHE_GLOBAL_NAMESPACES", ()))
    namespaces.update(getattr(settings, "ENDPOINT_CACHE_NAMESPACES", {}).get(route_name, ()))
    return tuple(sorted(namespaces))


def _build_authenticated_scope(request: HttpRequest) -> str:
    user = request.user
    if not user.is_authenticated:
        return "anonymous"

    session_key = request.session.session_key or "anonymous-session"
    return (
        f"user:{user.id}:session:{session_key}:"
        f"theme:{getattr(user, 'theme', 'white')}:super:{int(user.is_superuser)}"
    )


async def build_cache_scope(request: HttpRequest, route_name: str | None) -> str:
    if route_name in getattr(settings, "ENDPOINT_CSRF_CACHE_ROUTES", set()):
        return f"csrf:{get_token(request)}"

    return await sync_to_async(_build_authenticated_scope, thread_sensitive=True)(request)


async def get_namespace_versions(namespaces: tuple[str, ...]) -> dict[str, int]:
    if not namespaces:
        return {}

    version_keys = {
        namespace: f"{_CACHE_VERSION_PREFIX}:{namespace}"
        for namespace in namespaces
    }
    cached_versions = await sync_to_async(cache.get_many, thread_sensitive=False)(version_keys.values())
    return {
        namespace: int(cached_versions.get(version_key, 1) or 1)
        for namespace, version_key in version_keys.items()
    }


async def build_cache_key(request: HttpRequest, route_name: str) -> str:
    namespaces = get_route_cache_namespaces(route_name)
    versions = await get_namespace_versions(namespaces)
    scope = await build_cache_scope(request, route_name)
    path_digest = hashlib.sha256(request.get_full_path().encode("utf-8")).hexdigest()
    version_part = ":".join(f"{namespace}={versions[namespace]}" for namespace in namespaces)
    return f"{_CACHE_KEY_PREFIX}:{route_name}:{scope}:{path_digest}:{version_part}"


def serialize_response(response: HttpResponse) -> dict:
    return {
        "status_code": response.status_code,
        "content": bytes(response.content),
        "headers": {
            header: value
            for header, value in response.items()
            if header.lower() != "content-length"
        },
    }


def deserialize_response(payload: dict, method: str) -> HttpResponse:
    headers = dict(payload["headers"])
    content_type = headers.pop("Content-Type", None)
    body = b"" if method == "HEAD" else payload["content"]
    response = HttpResponse(
        content=body,
        status=payload["status_code"],
        content_type=content_type,
    )
    for header, value in headers.items():
        response[header] = value
    response["Content-Length"] = str(len(payload["content"]))
    response[CACHE_HEADER] = "HIT"
    return response


def is_cacheable_request(request: HttpRequest, route_name: str | None = None) -> tuple[bool, str | None, int]:
    route_name = route_name or resolve_route_name(request)
    timeout = get_route_cache_timeout(route_name)
    return request.method in _CACHEABLE_METHODS and timeout > 0, route_name, timeout


def is_cacheable_response(response: HttpResponse) -> bool:
    return not response.streaming and response.status_code in _CACHEABLE_STATUS_CODES


async def get_cached_response(request: HttpRequest, route_name: str) -> HttpResponse | None:
    cache_key = await build_cache_key(request, route_name)
    payload = await sync_to_async(cache.get, thread_sensitive=False)(cache_key)
    if payload is None:
        return None
    return deserialize_response(payload, request.method)


async def store_cached_response(request: HttpRequest, route_name: str, response: HttpResponse, timeout: int):
    cache_key = await build_cache_key(request, route_name)
    await sync_to_async(cache.set, thread_sensitive=False)(
        cache_key,
        serialize_response(response),
        timeout,
    )


async def invalidate_route_caches(*route_names: str, extra_namespaces: tuple[str, ...] = ()):
    namespaces = set(extra_namespaces)
    for route_name in route_names:
        namespaces.update(get_route_cache_namespaces(route_name))

    for namespace in namespaces:
        version_key = f"{_CACHE_VERSION_PREFIX}:{namespace}"
        try:
            await sync_to_async(cache.incr, thread_sensitive=False)(version_key)
        except ValueError:
            await sync_to_async(cache.set, thread_sensitive=False)(version_key, 2, None)
