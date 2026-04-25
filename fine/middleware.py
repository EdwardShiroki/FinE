from asgiref.sync import async_to_sync, iscoroutinefunction, sync_to_async
from django.shortcuts import render

from fine.cache_utils import (
    CACHE_HEADER,
    get_cached_response,
    is_cacheable_request,
    is_cacheable_response,
    store_cached_response,
)
from fine.services import queries
from fine.views import get_context


def endpoint_cache_middleware(get_response):
    if iscoroutinefunction(get_response):
        async def middleware(request):
            should_cache, route_name, timeout = is_cacheable_request(request)
            if not should_cache or route_name is None:
                response = await get_response(request)
                response.setdefault(CACHE_HEADER, "BYPASS")
                return response

            cached_response = await get_cached_response(request, route_name)
            if cached_response is not None:
                return cached_response

            response = await get_response(request)
            if not is_cacheable_response(response):
                response.setdefault(CACHE_HEADER, "SKIP")
                return response

            await store_cached_response(request, route_name, response, timeout)
            response[CACHE_HEADER] = "MISS"
            return response

        return middleware

    def middleware(request):
        should_cache, route_name, timeout = is_cacheable_request(request)
        if not should_cache or route_name is None:
            response = get_response(request)
            response.setdefault(CACHE_HEADER, "BYPASS")
            return response

        cached_response = async_to_sync(get_cached_response)(request, route_name)
        if cached_response is not None:
            return cached_response

        response = get_response(request)
        if not is_cacheable_response(response):
            response.setdefault(CACHE_HEADER, "SKIP")
            return response

        async_to_sync(store_cached_response)(request, route_name, response, timeout)
        response[CACHE_HEADER] = "MISS"
        return response

    return middleware


def async_not_found_page_middleware(get_response):
    if iscoroutinefunction(get_response):
        async def middleware(request):
            response = await get_response(request)
            if response.status_code != 404:
                return response

            await sync_to_async(queries.resolve_request_user, thread_sensitive=True)(request)
            context = get_context(request, "Ошибка")
            return await sync_to_async(render, thread_sensitive=True)(
                request,
                "pages/does_not_found.html",
                context,
                status=404,
            )

        return middleware

    def middleware(request):
        response = get_response(request)
        if response.status_code != 404:
            return response

        queries.resolve_request_user(request)
        context = get_context(request, "Ошибка")
        return render(request, "pages/does_not_found.html", context, status=404)

    return middleware
