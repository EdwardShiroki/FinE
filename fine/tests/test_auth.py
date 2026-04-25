from pathlib import Path

from django.conf import settings
from django.test import AsyncClient, TestCase, override_settings


class BaseTestCase(TestCase):
    """
    Тесты базового функционала
    """
    def setUp(self) -> None:
        """
        Настройка перед запуском теста
        """
        self.client = AsyncClient()

    async def test_running(self):
        """
        Тест того, что сервер запускается
        """
        response = await self.client.get("/")
        self.assertEqual(response.status_code, 200)

    async def test_missing_page_returns_async_404(self):
        response = await self.client.get("/missing-page/")
        self.assertEqual(response.status_code, 404)

    @override_settings(DEBUG=True)
    async def test_static_asset_is_served(self):
        response = await self.client.get("/fine/static/css/base.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response["Content-Type"])

    def test_project_is_asgi_only(self):
        self.assertEqual(settings.ASGI_APPLICATION, "fine_project.asgi.application")
        self.assertIsNone(getattr(settings, "WSGI_APPLICATION", None))
        self.assertFalse(Path(settings.BASE_DIR, "fine_project", "wsgi.py").exists())
