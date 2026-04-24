from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from fine.models import Event, UserRecommendation

DEFAULT_LIMIT = 50

def _event_score(user, event):
    score = 0.0

    if hasattr(user, "interests"):
        user_interest_values = set(user.interests.values_list("interest", flat=True))
        if event.entertainment_type in user_interest_values:
            score += 5.0

    members_count = event.members.count()
    score += min(members_count, 20) * 0.2

    days_to_start = (event.start_day - timezone.localdate()).days
    if days_to_start >= 0:
        score += max(0, 10 - days_to_start) * 0.1

    return score

def _candidate_events_for_user(user):
    qs = Event.objects.filter(status=True).exclude(author=user)
    qs = qs.exclude(members=user)
    return qs.select_related("author").prefetch_related("members")


async def _aevent_score(user, event):
    score = 0.0

    if hasattr(user, "interests"):
        user_interest_values = set(
            await sync_to_async(list, thread_sensitive=True)(
                user.interests.values_list("interest", flat=True)
            )
        )
        if event.entertainment_type in user_interest_values:
            score += 5.0

    members_count = await event.members.acount()
    score += min(members_count, 20) * 0.2

    days_to_start = (event.start_day - timezone.localdate()).days
    if days_to_start >= 0:
        score += max(0, 10 - days_to_start) * 0.1

    return score


def _acandidate_events_for_user(user):
    return _candidate_events_for_user(user)

@transaction.atomic
def generate_for_user(user, limit=DEFAULT_LIMIT):
    candidates = _candidate_events_for_user(user)
    scored = []

    for event in candidates:
        scored.append((event, _event_score(user, event)))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:limit]

    UserRecommendation.objects.filter(user=user).delete()

    now = timezone.now()
    bulk = [
        UserRecommendation(
            user=user,
            event=event,
            score=score,
            rank=idx + 1,
            generated_at=now,
        )
        for idx, (event, score) in enumerate(top)
    ]
    UserRecommendation.objects.bulk_create(bulk, batch_size=500)

def generate_for_all_users(limit=DEFAULT_LIMIT, batch_size=200):
    User = get_user_model()
    qs = User.objects.all().order_by("id")
    for user in qs.iterator(chunk_size=batch_size):
        generate_for_user(user=user, limit=limit)


async def agenerate_for_user(user, limit=DEFAULT_LIMIT):
    candidates = _acandidate_events_for_user(user)
    scored = []

    async for event in candidates:
        scored.append((event, await _aevent_score(user, event)))

    scored.sort(key=lambda item: item[1], reverse=True)
    top = scored[:limit]

    await UserRecommendation.objects.filter(user=user).adelete()

    now = timezone.now()
    bulk = [
        UserRecommendation(
            user=user,
            event=event,
            score=score,
            rank=idx + 1,
            generated_at=now,
        )
        for idx, (event, score) in enumerate(top)
    ]
    await UserRecommendation.objects.abulk_create(bulk, batch_size=500)


async def agenerate_for_all_users(limit=DEFAULT_LIMIT, batch_size=200):
    User = get_user_model()
    async for user in User.objects.all().order_by("id"):
        await agenerate_for_user(user=user, limit=limit)
