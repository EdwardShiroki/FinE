from asgiref.sync import sync_to_async
from django.db.models import Q
from django.utils import timezone

from fine.models import Event, Friends, Report, User, UserGroups, UserRecommendation
from fine.services.recommendations import agenerate_for_user


async def _alist(queryset):
    return [item async for item in queryset]


async def _aadd(manager, *objects):
    return await sync_to_async(manager.add, thread_sensitive=True)(*objects)


async def _aremove(manager, *objects):
    return await sync_to_async(manager.remove, thread_sensitive=True)(*objects)


async def _adelete(instance):
    return await sync_to_async(instance.delete, thread_sensitive=True)()


def resolve_request_user(request):
    user = request.user
    user.is_authenticated
    request.user = user
    return user


async def update_user_theme(user):
    new_theme = "dark" if user.theme == "white" else "white"
    await User.objects.filter(id=user.id).aupdate(theme=new_theme)
    user.theme = new_theme
    return new_theme


async def get_index_events():
    queryset = Event.objects.filter(type=Event.Type.OPEN).select_related("author")[:3]
    return await _alist(queryset)


async def get_menu_querysets(user, entertainment_type=None):
    filters = {"type": Event.Type.OPEN, "status": True}
    if entertainment_type and entertainment_type != "-1":
        filters["entertainment_type"] = entertainment_type

    events = await _alist(
        Event.objects.filter(**filters).select_related("author").order_by("start_day", "id")
    )

    private_events = []
    if user.is_authenticated:
        private_filters = {"type": Event.Type.CLOSE, "status": True}
        if entertainment_type and entertainment_type != "-1":
            private_filters["entertainment_type"] = entertainment_type
        private_events = await _alist(
            user.event_members.filter(**private_filters).select_related("author").order_by("start_day", "id")
        )

    return events, private_events


async def serialize_events_for_map(events):
    return [
        {
            "id": event.id,
            "name": event.name,
            "address": event.address,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "start_day": event.start_day.isoformat(),
            "finish_day": event.finish_day.isoformat(),
        }
        for event in events
        if event.latitude is not None and event.longitude is not None
    ]


async def get_recommendations_data(user, entertainment_type=None):
    recommendations_qs = UserRecommendation.objects.filter(user=user)
    if not await recommendations_qs.aexists():
        await agenerate_for_user(user)
        recommendations_qs = UserRecommendation.objects.filter(user=user)

    recommendations_qs = recommendations_qs.select_related("event", "event__author").order_by("rank")
    if entertainment_type and entertainment_type != "-1":
        recommendations_qs = recommendations_qs.filter(
            event__entertainment_type=entertainment_type
        )

    recommendations = await _alist(recommendations_qs)
    return recommendations, len(recommendations)


async def create_event_from_form(user, form):
    return await Event.objects.acreate(
        name=form.cleaned_data["name"],
        type=form.cleaned_data["type"],
        address=form.cleaned_data["address"],
        start_day=form.cleaned_data["start_day"],
        finish_day=form.cleaned_data["finish_day"],
        description=form.cleaned_data["description"],
        author=user,
        entertainment_type=form.cleaned_data["entertainment_type"],
        latitude=form.cleaned_data.get("latitude"),
        longitude=form.cleaned_data.get("longitude"),
    )


async def get_event_for_edit(event_id):
    return await Event.objects.select_related("author").aget(pk=event_id)


async def update_event_from_form(event_id, form):
    await Event.objects.filter(pk=event_id).aupdate(
        name=form.cleaned_data["name"],
        type=form.cleaned_data["type"],
        address=form.cleaned_data["address"],
        start_day=form.cleaned_data["start_day"],
        finish_day=form.cleaned_data["finish_day"],
        description=form.cleaned_data["description"],
        entertainment_type=form.cleaned_data["entertainment_type"],
        latitude=form.cleaned_data.get("latitude"),
        longitude=form.cleaned_data.get("longitude"),
    )
    return await get_event_for_edit(event_id)


async def add_user_to_event(user, event_id):
    event = await Event.objects.aget(pk=event_id)
    await _aadd(user.event_members, event)
    return event


async def add_group_members_to_event(user, event_id, group_id):
    event = await Event.objects.select_related("author").aget(pk=event_id)
    group = await UserGroups.objects.select_related("founder").aget(id=group_id)

    if user != event.author or user != group.founder:
        return None

    async for member in group.members.all():
        await _aadd(member.event_members, event)

    return event


async def get_profile_page_data(current_user, code):
    profile_user = await User.objects.aget(id=code)
    events = await _alist(profile_user.event_members.filter(type=Event.Type.OPEN).select_related("author"))
    my_events = await _alist(
        Event.objects.filter(author=profile_user, type=Event.Type.OPEN).select_related("author")
    )

    data = {
        "user": profile_user,
        "events": events,
        "my_events": my_events,
        "waiting_friend": None,
        "already_friend": None,
        "have_request": False,
    }

    if current_user.is_authenticated:
        relation = await Friends.objects.filter(
            from_user=current_user,
            to_user=profile_user,
        ).afirst()
        if relation is None:
            data["already_friend"] = False
        else:
            data["waiting_friend"] = relation.waiting

        data["have_request"] = await Friends.objects.filter(
            from_user=profile_user,
            to_user=current_user,
            waiting=True,
        ).aexists()

    return data


async def apply_profile_friend_action(current_user, code, action):
    target_user = await User.objects.aget(id=code)

    if action == "friend_button":
        await Friends.objects.acreate(from_user=current_user, to_user=target_user, waiting=True)
        return

    if action == "del_request":
        relation = await Friends.objects.aget(from_user=current_user, to_user=target_user)
        await _adelete(relation)
        return

    if action == "del_friend":
        relation = await Friends.objects.aget(from_user=current_user, to_user=target_user)
        reverse_relation = await Friends.objects.aget(from_user=target_user, to_user=current_user)
        await _adelete(relation)
        await _adelete(reverse_relation)
        return

    if action == "acp_friend":
        await Friends.objects.acreate(to_user=target_user, from_user=current_user, waiting=False)
        await Friends.objects.filter(
            to_user=current_user,
            from_user=target_user,
        ).aupdate(waiting=False)


async def get_event_page_data(current_user, event_id):
    event = await Event.objects.select_related("author").aget(id=event_id)
    people = await _alist(User.objects.filter(event_members__id=event_id))
    friend_ids = [
        relation.from_user_id
        async for relation in Friends.objects.filter(to_user=current_user, waiting=False)
    ]
    friends = await _alist(User.objects.filter(id__in=friend_ids, event_members__id=event_id))
    return event, people, friends


async def leave_event(user, event_id):
    event = await Event.objects.aget(id=event_id)
    await _aremove(user.event_members, event)


async def get_friends_page_data(user):
    return {
        "friends": await _alist(Friends.objects.filter(to_user=user, waiting=False).select_related("from_user")),
        "friends_request_to_user": await _alist(
            Friends.objects.filter(to_user=user, waiting=True).select_related("from_user")
        ),
        "friends_request_by_user": await _alist(
            Friends.objects.filter(from_user=user, waiting=True).select_related("to_user")
        ),
    }


async def apply_friends_action(user, post_data):
    cancel_to_request = post_data.get("cancel_to_request")
    if cancel_to_request:
        relation = await Friends.objects.aget(id=cancel_to_request)
        await _adelete(relation)
        return

    accept_from_request = post_data.get("accept_from_request")
    if accept_from_request:
        relation = await Friends.objects.select_related("from_user").aget(id=accept_from_request)
        await Friends.objects.acreate(
            to_user=relation.from_user,
            from_user=user,
            waiting=False,
        )
        await Friends.objects.filter(id=accept_from_request).aupdate(waiting=False)
        return

    cancel_from_request = post_data.get("cancel_from_request")
    if cancel_from_request:
        relation = await Friends.objects.aget(id=cancel_from_request)
        await _adelete(relation)
        return

    delete_friend = post_data.get("del_friend")
    if delete_friend:
        relation = await Friends.objects.aget(id=delete_friend)
        await Friends.objects.filter(
            Q(to_user=relation.to_user, from_user=relation.from_user)
            | Q(to_user=relation.from_user, from_user=relation.to_user)
        ).adelete()


async def create_group_from_form(user, form):
    return await UserGroups.objects.acreate(
        title=form.cleaned_data["title"],
        description=form.cleaned_data["description"],
        founder=user,
    )


async def get_groups_page_data(user, action, event_id=None):
    data = {
        "action": action,
        "buttons": "Информация" if action == "watch" else "Добавить",
        "my_groups": await _alist(UserGroups.objects.filter(founder=user)),
    }

    if action == "watch":
        data["groups"] = await _alist(user.members.all())
    elif action == "invite":
        data["event_id"] = event_id

    return data


async def get_group_page_data(user, group_id):
    group = await UserGroups.objects.select_related("founder").aget(id=group_id)
    group_users = await _alist(User.objects.filter(members__id=group_id))
    member_ids = [member_id async for member_id in user.members.values_list("id", flat=True)]
    return group, group_users, member_ids


async def delete_group(group):
    await _adelete(group)


async def remove_user_from_group(user, group):
    await _aremove(user.members, group)


async def get_search_friends_data(user, search_value=None):
    related_ids = {
        relation.to_user_id
        async for relation in Friends.objects.filter(from_user=user)
    }
    related_ids.update(
        {
            relation.from_user_id
            async for relation in Friends.objects.filter(to_user=user)
        }
    )

    queryset = User.objects.exclude(id__in=related_ids).exclude(id=user.id)
    if search_value:
        queryset = queryset.filter(
            Q(first_name__icontains=search_value)
            | Q(last_name__icontains=search_value)
            | Q(username__icontains=search_value)
        )

    users = await _alist(queryset.order_by("username"))
    return users, len(users)


async def create_friend_request(user, friend_id):
    target_user = await User.objects.aget(id=friend_id)
    await Friends.objects.acreate(from_user=user, to_user=target_user, waiting=True)


async def get_add_to_group_data(user, group_id, search_value=None):
    group = await UserGroups.objects.select_related("founder").aget(id=group_id)
    friend_ids = [
        relation.to_user_id
        async for relation in Friends.objects.filter(from_user=user, waiting=False)
    ]
    group_member_ids = [
        member_id async for member_id in User.objects.filter(members__id=group_id).values_list("id", flat=True)
    ]

    queryset = User.objects.filter(id__in=friend_ids).exclude(id__in=group_member_ids).exclude(id=user.id)
    if search_value:
        queryset = queryset.filter(
            Q(first_name__icontains=search_value)
            | Q(last_name__icontains=search_value)
            | Q(username__icontains=search_value)
        )

    users = await _alist(queryset.order_by("username"))
    return group, users, len(users)


async def invite_user_to_group(_current_user, group, invite_user_id):
    invited_user = await User.objects.aget(id=invite_user_id)
    await _aadd(invited_user.members, group)


async def get_remove_from_group_data(user, group_id, search_value=None):
    group = await UserGroups.objects.select_related("founder").aget(id=group_id)
    queryset = User.objects.filter(members__id=group_id).exclude(id=user.id)
    if search_value:
        queryset = queryset.filter(
            Q(first_name__icontains=search_value)
            | Q(last_name__icontains=search_value)
            | Q(username__icontains=search_value)
        )

    users = await _alist(queryset.order_by("username"))
    return group, users, len(users)


async def remove_member_from_group(delete_id, group_id):
    user = await User.objects.aget(id=delete_id)
    group = await UserGroups.objects.aget(id=group_id)
    await _aremove(user.members, group)


async def get_report_page_data(user, report_id):
    report = await Report.objects.select_related("author").aget(id=report_id)
    if report.author_id != user.id:
        return None
    return report


async def create_report(user, form):
    return await Report.objects.acreate(
        author=user,
        report_text=form.cleaned_data["report_text"],
        type=Report.Type.WAITING,
        created_at=timezone.now(),
    )


async def get_my_reports_data(user):
    reports = await _alist(Report.objects.filter(author=user).order_by("-created_at"))
    checked_reports = await Report.objects.filter(author=user, type=Report.Type.CLOSE).acount()
    return reports, checked_reports


async def get_unverified_reports():
    reports = await _alist(
        Report.objects.filter(type=Report.Type.WAITING).select_related("author").order_by("-created_at")
    )
    return reports, len(reports)


async def get_report_for_verification(report_id):
    return await Report.objects.select_related("author").aget(id=report_id)


async def verify_report(report_id, answer_text):
    await Report.objects.filter(id=report_id).aupdate(
        closed_at=timezone.now(),
        answer_text=answer_text,
        type=Report.Type.CLOSE,
    )
