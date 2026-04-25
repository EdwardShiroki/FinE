from asgiref.sync import iscoroutinefunction, sync_to_async
from django.shortcuts import render

from fine.services import queries
from fine.views import get_context


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
