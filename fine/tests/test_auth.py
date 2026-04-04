from django.test import TestCase, Client


class BaseTestCase(TestCase):
    """
    Тесты базового функционала
    """
    def setUp(self) -> None:
        """
        Настройка перед запуском теста
        """
        self.client = Client()

    def test_running(self):
        """
        Тест того, что сервер запускается
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
