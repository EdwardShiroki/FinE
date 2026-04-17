from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from fine.models import Event, UserRecommendation


class FeedRecommendationsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
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

    def test_feed_triggers_generation_when_user_has_no_recommendations(self):
        self.client.force_login(self.viewer)
        self.assertFalse(UserRecommendation.objects.filter(user=self.viewer).exists())

        response = self.client.get(reverse("feed"))

        self.assertEqual(response.status_code, 200)
        recommendations = UserRecommendation.objects.filter(user=self.viewer)
        self.assertTrue(recommendations.exists())
        self.assertEqual(recommendations.first().event_id, self.event.id)
        self.assertGreater(response.context["recommendations_size"], 0)
