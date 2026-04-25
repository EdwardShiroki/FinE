import random
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from fine.models import Event, Friends, Report, UserGroups, UserRecommendation, UserSettings

DEMO_USERNAME_PREFIX = "demo_user_"
DEMO_EMAIL_DOMAIN = "fine-demo.local"
DEMO_EVENT_PREFIX = "Событие СПБ #"
DEMO_GROUP_PREFIX = "grp_"
DEFAULT_PASSWORD = "demo-pass-123"
DEFAULT_SEED = 20260425


@dataclass(frozen=True)
class SpbLocation:
    district: str
    street: str
    latitude: float
    longitude: float


SPB_LOCATIONS = [
    SpbLocation("Центральный район", "Невский проспект", 59.9343, 30.3351),
    SpbLocation("Адмиралтейский район", "Гороховая улица", 59.9257, 30.3162),
    SpbLocation("Петроградский район", "Каменноостровский проспект", 59.9660, 30.3090),
    SpbLocation("Василеостровский район", "Большой проспект В.О.", 59.9438, 30.2677),
    SpbLocation("Московский район", "Московский проспект", 59.8518, 30.3216),
    SpbLocation("Приморский район", "Богатырский проспект", 59.9958, 30.2407),
    SpbLocation("Выборгский район", "проспект Энгельса", 60.0393, 30.3216),
    SpbLocation("Калининский район", "Гражданский проспект", 60.0354, 30.4090),
    SpbLocation("Фрунзенский район", "Бухарестская улица", 59.8718, 30.3856),
    SpbLocation("Невский район", "проспект Большевиков", 59.9182, 30.4723),
]

FIRST_NAMES = [
    "Алексей",
    "Мария",
    "Иван",
    "Анна",
    "Дмитрий",
    "Елена",
    "Сергей",
    "Ольга",
    "Максим",
    "Наталья",
]

LAST_NAMES = [
    "Иванов",
    "Петров",
    "Сидоров",
    "Смирнова",
    "Кузнецов",
    "Попова",
    "Волков",
    "Федорова",
    "Морозов",
    "Павлова",
]

USER_STATUSES = [
    "На связи",
    "Ищу компанию",
    "Готов к новым знакомствам",
    "Открыт к мероприятиям",
]

REPORT_TOPICS = [
    "Нужно проверить описание мероприятия",
    "Есть вопрос по участникам",
    "Хочу уточнить правила входа",
    "Подозрение на дублирующее событие",
]


class Command(BaseCommand):
    help = "Generate demo data set with Saint Petersburg events"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=1000)
        parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
        parser.add_argument("--password", default=DEFAULT_PASSWORD)

    def handle(self, *args, **options):
        count = options["count"]
        if count <= 0:
            raise ValueError("--count must be greater than zero")

        password = options["password"]
        rng = random.Random(options["seed"])
        user_model = get_user_model()

        self.stdout.write(
            f"Seeding demo data: count={count}, seed={options['seed']}, city=Saint Petersburg"
        )

        with transaction.atomic():
            self._clear_existing_demo_data(user_model)
            users = self._create_users(user_model, count, password)
            self._create_user_settings(users)
            events = self._create_events(users, count, rng)
            self._create_event_memberships(users, events, rng)
            self._create_reports(users, count, rng)
            self._create_friendships(users, count)
            groups = self._create_groups(users, count)
            self._create_group_memberships(users, groups, rng)
            self._create_recommendations(users, events, count, rng)

        self.stdout.write(self.style.SUCCESS(f"Created {count} rows for each demo model"))
        self.stdout.write(f"Demo users password: {password}")

    def _clear_existing_demo_data(self, user_model):
        deleted_count, _ = user_model.objects.filter(
            username__startswith=DEMO_USERNAME_PREFIX
        ).delete()
        self.stdout.write(f"Removed existing demo rows: {deleted_count}")

    def _create_users(self, user_model, count, password):
        password_hash = make_password(password)
        users = []
        for index in range(count):
            users.append(
                user_model(
                    username=f"{DEMO_USERNAME_PREFIX}{index + 1:04d}",
                    email=f"{DEMO_USERNAME_PREFIX}{index + 1:04d}@{DEMO_EMAIL_DOMAIN}",
                    first_name=FIRST_NAMES[index % len(FIRST_NAMES)],
                    last_name=LAST_NAMES[(index + 3) % len(LAST_NAMES)],
                    status=USER_STATUSES[index % len(USER_STATUSES)],
                    theme="dark" if index % 2 else "white",
                    password=password_hash,
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                )
            )

        user_model.objects.bulk_create(users, batch_size=500)
        return list(
            user_model.objects.filter(username__startswith=DEMO_USERNAME_PREFIX).order_by("id")
        )

    def _create_user_settings(self, users):
        UserSettings.objects.bulk_create(
            [UserSettings(user=user) for user in users],
            batch_size=500,
        )

    def _create_events(self, users, count, rng):
        today = timezone.localdate()
        events = []
        for index in range(count):
            location = SPB_LOCATIONS[index % len(SPB_LOCATIONS)]
            start_offset = rng.randint(1, 120)
            duration = rng.randint(0, 2)
            lat_jitter = rng.uniform(-0.015, 0.015)
            lon_jitter = rng.uniform(-0.025, 0.025)
            house_number = rng.randint(1, 250)
            entertainment_type = rng.choice(list(Event._meta.get_field("entertainment_type").choices))[0]
            events.append(
                Event(
                    name=f"{DEMO_EVENT_PREFIX}{index + 1:04d}",
                    type=Event.Type.OPEN if index % 3 else Event.Type.CLOSE,
                    address=f"Санкт-Петербург, {location.street}, д. {house_number}",
                    status=index % 10 != 0,
                    start_day=today + timedelta(days=start_offset),
                    finish_day=today + timedelta(days=start_offset + duration),
                    description=(
                        f"Тестовое мероприятие в Санкт-Петербурге. "
                        f"Район: {location.district}. "
                        f"Подходит для проверки ленты, карты и рекомендаций."
                    ),
                    author=users[index % len(users)],
                    entertainment_type=entertainment_type,
                    latitude=round(location.latitude + lat_jitter, 6),
                    longitude=round(location.longitude + lon_jitter, 6),
                )
            )

        Event.objects.bulk_create(events, batch_size=500)
        return list(Event.objects.filter(name__startswith=DEMO_EVENT_PREFIX).order_by("id"))

    def _create_event_memberships(self, users, events, rng):
        through_model = Event.members.through
        memberships = []
        for index, event in enumerate(events):
            available_members = [user for user in users if user.id != event.author_id]
            target_members_count = min(3, len(available_members))
            if not target_members_count:
                continue

            for member in rng.sample(available_members, k=target_members_count):
                memberships.append(
                    through_model(event_id=event.id, user_id=member.id)
                )

        through_model.objects.bulk_create(memberships, batch_size=1000)

    def _create_reports(self, users, count, rng):
        now = timezone.now()
        reports = []
        for index in range(count):
            is_closed = index % 4 == 0
            created_at = now - timedelta(days=rng.randint(0, 30), hours=rng.randint(0, 23))
            reports.append(
                Report(
                    author=users[index % len(users)],
                    report_text=(
                        f"Демо-обращение #{index + 1:04d}. {REPORT_TOPICS[index % len(REPORT_TOPICS)]}."
                    ),
                    answer_text="Вопрос обработан демо-скриптом." if is_closed else None,
                    created_at=created_at,
                    closed_at=created_at + timedelta(hours=6) if is_closed else None,
                    type=Report.Type.CLOSE if is_closed else Report.Type.WAITING,
                )
            )

        Report.objects.bulk_create(reports, batch_size=500)

    def _create_friendships(self, users, count):
        friendships = []
        half = count // 2
        for index in range(half):
            left_user = users[index]
            right_user = users[index + half]
            friendships.append(Friends(from_user=left_user, to_user=right_user, waiting=False))
            friendships.append(Friends(from_user=right_user, to_user=left_user, waiting=False))

        if count % 2:
            friendships.append(Friends(from_user=users[-1], to_user=users[0], waiting=True))

        Friends.objects.bulk_create(friendships[:count], batch_size=500)

    def _create_groups(self, users, count):
        groups = [
            UserGroups(
                title=f"{DEMO_GROUP_PREFIX}{index + 1:04d}",
                description=f"Демо-группа #{index + 1:04d} для проверки приглашений и состава участников.",
                founder=users[index % len(users)],
            )
            for index in range(count)
        ]

        UserGroups.objects.bulk_create(groups, batch_size=500)
        return list(UserGroups.objects.filter(title__startswith=DEMO_GROUP_PREFIX).order_by("id"))

    def _create_group_memberships(self, users, groups, rng):
        through_model = UserGroups.members.through
        memberships = []
        for index, group in enumerate(groups):
            member_ids = {group.founder_id}
            target_members_count = min(4, len(users))
            while len(member_ids) < target_members_count:
                member_ids.add(users[(index + rng.randint(0, len(users) - 1)) % len(users)].id)

            for member_id in member_ids:
                memberships.append(through_model(usergroups_id=group.id, user_id=member_id))

        through_model.objects.bulk_create(memberships, batch_size=1000)

    def _create_recommendations(self, users, events, count, rng):
        recommendations = []
        total_events = len(events)
        generated_at = timezone.now()
        for index in range(count):
            user = users[index % len(users)]
            event = events[(index + 17) % total_events]
            if event.author_id == user.id:
                event = events[(index + 18) % total_events]

            recommendations.append(
                UserRecommendation(
                    user=user,
                    event=event,
                    score=round(rng.uniform(3.5, 9.9), 2),
                    rank=1,
                    generated_at=generated_at,
                )
            )

        UserRecommendation.objects.bulk_create(recommendations, batch_size=500)
