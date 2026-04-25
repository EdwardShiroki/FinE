from datetime import timedelta

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.test import AsyncClient, TestCase
from django.urls import reverse
from django.utils import timezone

from fine.models import Event, UserRecommendation


class FeedRecommendationsTestCase(TestCase):
    def setUp(self):
        self.client = AsyncClient()
        user_model = get_user_model()

        self.viewer = user_model.objects.create_user(
            username="viewer",
            password="viewer-pass-123",
            status="",
        )
        self.author = user_model.objects.create_user(
            username="author",
            password="author-pass-123",
            status="",
        )

        today = timezone.localdate()
        self.event = Event.objects.create(
            name="Generated recommendation event",
            type=Event.Type.OPEN,
            address="Moscow",
            status=True,
            start_day=today + timedelta(days=2),
            finish_day=today + timedelta(days=2),
            description="Event for recommendations generation test",
            author=self.author,
        )

    async def test_feed_triggers_generation_when_user_has_no_recommendations(self):
        await sync_to_async(self.client.force_login, thread_sensitive=True)(self.viewer)
        self.assertFalse(
            await sync_to_async(
                lambda: UserRecommendation.objects.filter(user=self.viewer).exists(),
                thread_sensitive=True,
            )()
        )

        response = await self.client.get(reverse("feed"))

        self.assertEqual(response.status_code, 200)
        recommendations = await sync_to_async(
            lambda: list(UserRecommendation.objects.filter(user=self.viewer).order_by("rank")),
            thread_sensitive=True,
        )()
        self.assertTrue(recommendations)
        self.assertEqual(recommendations[0].event_id, self.event.id)
        self.assertGreater(response.context["recommendations_size"], 0)
