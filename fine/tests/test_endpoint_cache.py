import asyncio
from unittest.mock import AsyncMock, patch

from asgiref.sync import sync_to_async
from django.core.cache import cache
from django.test import AsyncClient, TestCase, override_settings
from django.urls import reverse


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "endpoint-cache-tests",
        }
    },
    ENDPOINT_CACHE_GLOBAL_NAMESPACES=("theme",),
    ENDPOINT_CACHE_TIMEOUTS={
        "index": 1,
        "menu": 60,
        "theme_change": 0,
    },
    ENDPOINT_CACHE_NAMESPACES={
        "index": ("events",),
        "menu": ("events",),
    },
    ENDPOINT_CSRF_CACHE_ROUTES=set(),
)
class EndpointCacheMiddlewareTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = AsyncClient()
        self.user = self.user_model.objects.create_user(
            username="cache-user",
            password="cache-pass-123",
            status="",
        )

    @property
    def user_model(self):
        from django.contrib.auth import get_user_model

        return get_user_model()

    async def test_index_page_uses_cached_response_until_ttl_expires(self):
        with patch(
            "fine.services.queries.get_index_events",
            new=AsyncMock(return_value=[]),
        ) as get_index_events:
            first_response = await self.client.get(reverse("index"))
            second_response = await self.client.get(reverse("index"))

            self.assertEqual(first_response["X-Endpoint-Cache"], "MISS")
            self.assertEqual(second_response["X-Endpoint-Cache"], "HIT")
            self.assertEqual(get_index_events.await_count, 1)

            await asyncio.sleep(1.1)

            third_response = await self.client.get(reverse("index"))
            self.assertEqual(third_response["X-Endpoint-Cache"], "MISS")
            self.assertEqual(get_index_events.await_count, 2)

    async def test_theme_change_invalidates_existing_menu_cache(self):
        await sync_to_async(self.client.force_login, thread_sensitive=True)(self.user)

        with patch(
            "fine.services.queries.get_menu_querysets",
            new=AsyncMock(return_value=([], [])),
        ) as get_menu_querysets:
            first_response = await self.client.get(reverse("menu"))
            second_response = await self.client.get(reverse("menu"))

            self.assertEqual(first_response["X-Endpoint-Cache"], "MISS")
            self.assertEqual(second_response["X-Endpoint-Cache"], "HIT")
            self.assertEqual(get_menu_querysets.await_count, 1)

            theme_response = await self.client.get(reverse("theme_change"))
            self.assertEqual(theme_response["X-Endpoint-Cache"], "BYPASS")

            third_response = await self.client.get(reverse("menu"))
            self.assertEqual(third_response["X-Endpoint-Cache"], "MISS")
            self.assertEqual(get_menu_querysets.await_count, 2)
