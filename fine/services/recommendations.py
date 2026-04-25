from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

from fine.models import Event, UserRecommendation

DEFAULT_LIMIT = 50


def _event_score(user_interest_values, event):
    score = 0.0

    if event.entertainment_type in user_interest_values:
        score += 5.0

    members_count = getattr(event, "members_count", 0)
    score += min(members_count, 20) * 0.2

    days_to_start = (event.start_day - timezone.localdate()).days
    if days_to_start >= 0:
        score += max(0, 10 - days_to_start) * 0.1

    return score

def _candidate_events_for_user(user):
    return (
        Event.objects.filter(status=True)
        .exclude(author=user)
        .exclude(members=user)
        .select_related("author")
        .annotate(members_count=Count("members"))
        .order_by("start_day", "id")
    )


async def _user_interest_values(user):
    if not hasattr(user, "interests"):
        return set()
    return {
        interest
        async for interest in user.interests.values_list("interest", flat=True)
    }


async def agenerate_for_user(user, limit=DEFAULT_LIMIT):
    candidates = _candidate_events_for_user(user)
    user_interest_values = await _user_interest_values(user)
    scored = []

    async for event in candidates:
        scored.append((event, _event_score(user_interest_values, event)))

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
    async for user in User.objects.all().order_by("id").aiterator(chunk_size=batch_size):
        await agenerate_for_user(user=user, limit=limit)
