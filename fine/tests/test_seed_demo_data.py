from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from fine.models import Event, Friends, Report, UserGroups, UserRecommendation, UserSettings


class SeedDemoDataCommandTestCase(TestCase):
    def test_command_creates_requested_amount_and_resets_previous_demo_rows(self):
        call_command("seed_demo_data", count=5, seed=123, password="demo-test-pass")

        user_model = get_user_model()
        self.assertEqual(user_model.objects.filter(username__startswith="demo_user_").count(), 5)
        self.assertEqual(UserSettings.objects.count(), 5)
        self.assertEqual(Event.objects.count(), 5)
        self.assertEqual(Report.objects.count(), 5)
        self.assertEqual(Friends.objects.count(), 5)
        self.assertEqual(UserGroups.objects.count(), 5)
        self.assertEqual(UserRecommendation.objects.count(), 5)

        first_user = user_model.objects.get(username="demo_user_0001")
        self.assertTrue(first_user.check_password("demo-test-pass"))

        for event in Event.objects.all():
            self.assertIn("Санкт-Петербург", event.address)
            self.assertGreaterEqual(event.latitude, 59.80)
            self.assertLessEqual(event.latitude, 60.10)
            self.assertGreaterEqual(event.longitude, 30.15)
            self.assertLessEqual(event.longitude, 30.55)

        call_command("seed_demo_data", count=3, seed=456)

        self.assertEqual(user_model.objects.filter(username__startswith="demo_user_").count(), 3)
        self.assertEqual(UserSettings.objects.count(), 3)
        self.assertEqual(Event.objects.count(), 3)
        self.assertEqual(Report.objects.count(), 3)
        self.assertEqual(Friends.objects.count(), 3)
        self.assertEqual(UserGroups.objects.count(), 3)
        self.assertEqual(UserRecommendation.objects.count(), 3)
