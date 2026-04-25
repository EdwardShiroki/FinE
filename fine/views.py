import json
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.defaultfilters import register
from django.urls import reverse
from django.utils._os import safe_join

from fine.cache_utils import invalidate_route_caches
from fine.forms import (
    CreateEvent,
    CreateGroup,
    CreateReportForm,
    EditProfile,
    RegistrationForm,
    SearchFriends,
    VerifyReportForm,
)
from fine.models import Event, Report, User, UserGroups
from fine.services import queries

EVENT_CACHE_ROUTES = (
    "index",
    "menu",
    "feed",
    "profile",
    "event",
    "event_create",
    "event_edit",
)
FRIEND_CACHE_ROUTES = (
    "profile",
    "friends",
    "search_friends",
    "event",
    "add_to_group",
)
GROUP_CACHE_ROUTES = (
    "groups",
    "group",
    "create_group",
    "add_to_group",
    "remove_from_the_group",
)
REPORT_CACHE_ROUTES = (
    "my_reports",
    "create_report",
    "report",
    "verify_report",
    "unverifed_reports",
)


@register.filter
def is_authenticated(menu_dict: dict, is_auth: bool):
    if is_auth:
        return menu_dict["authorized"]
    return menu_dict["unauthorized"]


@register.filter
def is_active(first_url: str, second_url: str):
    if first_url == second_url:
        return "active"
    return ""


@register.filter
def get_style(item: dict):
    return item.get("button-style", "btn-primary")


@register.filter
def get_theme(request: HttpRequest):
    if request.user.is_authenticated and request.user.theme == "dark":
        return "dark"
    return ""


@register.filter
def normalize_page_name(value: str):
    if not isinstance(value, str):
        return value

    normalized = {
        "Wellcome": "Главная",
        "Error": "Ошибка",
        "Р СљР ВµР Р…РЎР‹": "Мероприятия",
        "Р В Р ВµР С”Р С•Р СР ВµР Р…Р Т‘Р В°РЎвЂ Р С‘Р С‘": "Рекомендации",
        "Р В Р ВµР С–Р С‘РЎРѓРЎвЂљРЎР‚Р В°РЎвЂ Р С‘РЎРЏ": "Регистрация",
        "Р РЋР С•Р В·Р Т‘Р В°Р Р…Р С‘Р Вµ Р СР ВµРЎР‚Р С•Р С—РЎР‚Р С‘РЎРЏРЎвЂљР С‘РЎРЏ": "Создание мероприятия",
        "Р В Р ВµР Т‘Р В°Р С”РЎвЂљР С‘РЎР‚Р С•Р Р†Р В°Р Р…Р С‘Р Вµ Р СР ВµРЎР‚Р С•Р С—РЎР‚Р С‘РЎРЏРЎвЂљР С‘РЎРЏ": "Редактирование мероприятия",
        "Р СџРЎР‚Р С•РЎвЂћР С‘Р В»РЎРЉ": "Профиль",
        "Р В Р ВµР Т‘Р В°Р С”РЎвЂљР С‘РЎР‚Р С•Р Р†Р В°Р Р…Р С‘Р Вµ Р С—РЎР‚Р С•РЎвЂћР С‘Р В»РЎРЏ": "Редактирование профиля",
        "Р СљР ВµРЎР‚Р С•Р С—РЎР‚Р С‘РЎРЏРЎвЂљР С‘Р Вµ": "Мероприятие",
        "Р вЂќРЎР‚РЎС“Р В·РЎРЉРЎРЏ": "Друзья",
        "Р РЋР С•Р В·Р Т‘Р В°Р Р…Р С‘Р Вµ Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№": "Создание группы",
        "Р вЂњРЎР‚РЎС“Р С—Р С—РЎвЂ№": "Группы",
        "Р СџР С•Р С‘РЎРѓР С” Р Т‘РЎР‚РЎС“Р В·Р ВµР в„–": "Поиск друзей",
        "Р РЋР С•Р В·Р Т‘Р В°Р Р…Р С‘Р Вµ Р В¶Р В°Р В»Р С•Р В±РЎвЂ№": "Создание жалобы",
        "Р СљР С•Р С‘ Р В¶Р В°Р В»Р С•Р В±РЎвЂ№": "Мои жалобы",
        "Р СџРЎР‚Р С•Р Р†Р ВµРЎР‚Р С”Р В° Р В¶Р В°Р В»Р С•Р В±": "Проверка жалоб",
        "РђРІС‚РѕСЂРёР·Р°С†РёСЏ": "Авторизация",
    }
    if value in normalized:
        return normalized[value]
    if value.startswith("Р вЂњРЎР‚РЎС“Р С—Р С—Р В° РІвЂћвЂ“"):
        return "Группа №" + value.split("вЂ“", 1)[-1]
    if value.startswith("Р вЂќР С•Р В±Р В°Р Р†Р В»Р ВµР Р…Р С‘Р Вµ Р Р† Р С–РЎР‚РЎС“Р С—Р С—РЎС“ РІвЂћвЂ“"):
        return "Добавление в группу №" + value.split("вЂ“", 1)[-1]
    if value.startswith("Р Р€Р Т‘Р В°Р В»Р ВµР Р…Р С‘Р Вµ Р С‘Р В· Р С–РЎР‚РЎС“Р С—Р С—РЎвЂ№ РІвЂћвЂ“"):
        return "Удаление из группы №" + value.split("вЂ“", 1)[-1]
    if value.startswith("Р вЂ“Р В°Р В»Р С•Р В±Р В° РІвЂћвЂ“"):
        return "Жалоба №" + value.split("вЂ“", 1)[-1]
    return value


def get_context(request: HttpRequest | None = None, page_name: str = "", active: str = "") -> dict:
    data = {
        "pagename": page_name,
        "active": active,
        "yandex_maps_api_key": settings.YANDEX_MAPS_API_KEY,
        "menu": {
            "left": {
                "unauthorized": [
                    {"url_name": "/", "name": "Главная страница"},
                    {"url_name": "/menu/", "name": "Меню"},
                ],
            },
            "right": {
                "unauthorized": [
                    {"url_name": "/registration/", "name": "Зарегистрироваться"},
                    {
                        "url_name": "/login/",
                        "name": "Войти",
                        "button-style": "btn-outline-primary",
                    },
                ],
            },
        },
    }
    if request is None:
        return data

    if request.user.is_authenticated:
        data["menu"]["left"]["authorized"] = [
            {"url_name": reverse("index"), "name": "Главная страница"},
            {"url_name": reverse("menu"), "name": "Меню"},
            {"url_name": reverse("feed"), "name": "Рекомендации"},
            {"url_name": reverse("friends"), "name": "Друзья"},
            {"url_name": reverse("search_friends"), "name": "Найти друга"},
        ]
        data["menu"]["right"]["authorized"] = [
            {
                "url_name": reverse("unverifed_reports")
                if request.user.is_superuser
                else reverse("my_reports"),
                "name": "Жалобы",
            },
            {"url_name": "/groups?action=watch", "name": "Группы"},
            {
                "url_name": reverse("profile", kwargs={"code": request.user.id}),
                "name": "Профиль",
            },
            {
                "url_name": reverse("logout"),
                "name": "Выйти",
                "button-style": "btn-outline-primary",
            },
        ]
    return data


async def _load_request_user(request: HttpRequest):
    return await sync_to_async(queries.resolve_request_user, thread_sensitive=True)(request)


async def _async_render(request: HttpRequest, template_name: str, context: dict, status: int = 200):
    return await sync_to_async(render, thread_sensitive=True)(
        request,
        template_name,
        context,
        status=status,
    )


async def _async_redirect(*args, **kwargs):
    return await sync_to_async(redirect, thread_sensitive=True)(*args, **kwargs)


async def _async_form_is_valid(form):
    return await sync_to_async(form.is_valid, thread_sensitive=True)()


async def _async_form_save(form):
    return await sync_to_async(form.save, thread_sensitive=True)()


async def _add_error_message(request: HttpRequest, message: str):
    await sync_to_async(messages.error, thread_sensitive=True)(request, message)


async def _require_login(request: HttpRequest):
    user = await _load_request_user(request)
    if user.is_authenticated:
        return None
    next_url = quote(request.get_full_path(), safe="/?=&")
    return await _async_redirect(f"{settings.LOGIN_URL}?next={next_url}")


async def _invalidate_cache(*route_names: str, extra_namespaces: tuple[str, ...] = ()):
    await invalidate_route_caches(*route_names, extra_namespaces=extra_namespaces)


async def _serve_file(document_root: str, path: str):
    try:
        resolved_path = safe_join(document_root, path)
    except ValueError as exc:
        raise Http404 from exc

    file_exists = await sync_to_async(os.path.isfile, thread_sensitive=True)(resolved_path)
    if not file_exists:
        raise Http404

    content = await sync_to_async(Path(resolved_path).read_bytes, thread_sensitive=True)()
    content_type, encoding = mimetypes.guess_type(resolved_path)
    response = HttpResponse(content, content_type=content_type or "application/octet-stream")
    response["Content-Length"] = str(len(content))
    if encoding:
        response["Content-Encoding"] = encoding
    return response


async def login_page(request: HttpRequest):
    await _load_request_user(request)
    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.user.is_authenticated:
        return await _async_redirect(next_url or settings.LOGIN_REDIRECT_URL)

    context = get_context(request, "Авторизация", reverse("login"))
    context["menu"]["right"]["unauthorized"][1] = {
        "url_name": "/login/",
        "name": "Войти",
    }

    form = AuthenticationForm(request=request, data=request.POST or None)
    if request.method == "POST" and await _async_form_is_valid(form):
        await sync_to_async(auth_login, thread_sensitive=True)(request, form.get_user())
        return await _async_redirect(next_url or settings.LOGIN_REDIRECT_URL)

    context["form"] = form
    context["next"] = next_url
    return await _async_render(request, "registration/login.html", context)


async def logout_page(request: HttpRequest):
    await sync_to_async(auth_logout, thread_sensitive=True)(request)
    return await _async_redirect(settings.LOGOUT_REDIRECT_URL)


async def theme_change(request: HttpRequest):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    await queries.update_user_theme(request.user)
    await _invalidate_cache(extra_namespaces=("theme",))
    return JsonResponse({"details": "ok"})


async def index_page(request: HttpRequest):
    await _load_request_user(request)
    context = get_context(request, "Главная", reverse("index"))
    context["events"] = await queries.get_index_events()
    return await _async_render(request, "pages/start/index.html", context)


async def error_page(request: HttpRequest):
    await _load_request_user(request)
    context = get_context(request, "Ошибка")
    return await _async_render(request, "pages/does_not_found.html", context, status=404)


async def static_file(request: HttpRequest, path: str):
    del request
    document_root = f"{settings.BASE_DIR}/fine/static" if settings.DEBUG else settings.STATIC_ROOT
    return await _serve_file(document_root, path)


async def media_file(request: HttpRequest, path: str):
    del request
    return await _serve_file(settings.MEDIA_ROOT, path)


async def menu_page(request: HttpRequest):
    await _load_request_user(request)
    context = get_context(request, "Меню", reverse("menu"))
    entertainment_type = request.POST.get("entertainment_type") if request.method == "POST" else None

    events, private_events = await queries.get_menu_querysets(request.user, entertainment_type)

    context["events"] = events
    context["events_map_data"] = await queries.serialize_events_for_map(events)
    context["user"] = request.user
    if request.user.is_authenticated:
        context["private_events"] = private_events

    return await _async_render(request, "pages/start/menu.html", context)


async def feed_page(request: HttpRequest):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "Рекомендации", reverse("feed"))
    recommendations, recommendations_size = await queries.get_recommendations_data(
        request.user,
        request.POST.get("entertainment_type") if request.method == "POST" else None,
    )
    context["recommendations"] = recommendations
    context["recommendations_size"] = recommendations_size
    return await _async_render(request, "pages/main/feed.html", context)


async def registration_page(request: HttpRequest):
    await _load_request_user(request)
    context = get_context(request, "Регистрация", reverse("register"))
    form = RegistrationForm(request.POST or None)

    if request.method == "POST":
        if await _async_form_is_valid(form):
            await User.objects.acreate(
                username=form.cleaned_data["username"],
                password=make_password(form.cleaned_data["password2"]),
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=form.cleaned_data["email"],
            )
            return await _async_redirect("/")
        context["errors"] = form.errors

    context["form"] = form
    return await _async_render(request, "registration/register.html", context)


async def event_create_page(request: HttpRequest):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "Создание мероприятия")
    context["today"] = str(datetime.today().date())
    form = CreateEvent(request.POST or None)

    if request.method == "POST":
        if await _async_form_is_valid(form):
            if form.cleaned_data["start_day"] <= form.cleaned_data["finish_day"]:
                event = await queries.create_event_from_form(request.user, form)
                await _invalidate_cache(*EVENT_CACHE_ROUTES)
                return await _async_redirect(reverse("event_commit", kwargs={"event_id": event.id}))
            await _add_error_message(
                request,
                "Дата окончания не может быть раньше даты начала.",
            )
        context["errors"] = form.errors

    context["form"] = form
    return await _async_render(request, "pages/event/create.html", context)


async def event_edit_page(request: HttpRequest, event_id: int):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    try:
        event = await queries.get_event_for_edit(event_id)
    except Event.DoesNotExist as exc:
        raise Http404 from exc

    context = get_context(request, "Редактирование мероприятия")
    context["event_id"] = event_id
    context["event"] = event
    form = CreateEvent(request.POST or None, instance=event)

    if request.method == "POST" and await _async_form_is_valid(form):
        context["event"] = await queries.update_event_from_form(event_id, form)
        await _invalidate_cache(*EVENT_CACHE_ROUTES)

    context["form"] = form
    return await _async_render(request, "pages/event/edit.html", context)


async def commit_event_page(request: HttpRequest, event_id: int):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    try:
        await queries.add_user_to_event(request.user, event_id)
    except Event.DoesNotExist:
        return await _async_redirect(reverse("event", kwargs={"event_id": event_id}))

    await _invalidate_cache("event", "menu", "feed", "profile")
    return await _async_redirect(reverse("event", kwargs={"event_id": event_id}))


async def commit_event_group_page(request: HttpRequest, event_id: int, group_id: int):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    try:
        event = await queries.add_group_members_to_event(request.user, event_id, group_id)
    except (Event.DoesNotExist, UserGroups.DoesNotExist):
        return await _async_redirect("/")

    if event is None:
        return await _async_redirect("/")

    await _invalidate_cache("event", "menu", "feed", "profile", *GROUP_CACHE_ROUTES)
    return await _async_redirect(reverse("event", kwargs={"event_id": event_id}))


async def profile_view_page(request: HttpRequest, code: int):
    await _load_request_user(request)
    context = get_context(request, "Профиль", reverse("profile", kwargs={"code": code}))

    try:
        profile_data = await queries.get_profile_page_data(request.user, code)
    except User.DoesNotExist as exc:
        raise Http404 from exc

    context["user"] = profile_data["user"]
    context["events"] = profile_data["events"]
    context["my_events"] = profile_data["my_events"]
    if profile_data["waiting_friend"] is not None:
        context["waiting_friend"] = profile_data["waiting_friend"]
    if profile_data["already_friend"] is not None:
        context["already_friend"] = profile_data["already_friend"]
    context["have_request"] = profile_data["have_request"]

    if request.method == "POST":
        await queries.apply_profile_friend_action(request.user, code, request.POST.get("button"))
        await _invalidate_cache(*FRIEND_CACHE_ROUTES, "profile")
        return await _async_redirect(f"/profile/{code}")

    return await _async_render(request, "pages/profile/view.html", context)


async def edit_page(request: HttpRequest):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    cur_user = await User.objects.aget(username=request.user.username)
    context = get_context(request, "Редактирование профиля", reverse("profile", kwargs={"code": request.user.id}))
    form = EditProfile(request.POST or None, request.FILES or None, instance=cur_user)

    if request.method == "POST":
        if await _async_form_is_valid(form):
            await _async_form_save(form)
            await _invalidate_cache("profile", "edition_about")
        return await _async_redirect(f"/profile/{request.user.id}")

    context["form"] = form
    return await _async_render(request, "pages/profile/edit_about.html", context)


async def event_page(request: HttpRequest, event_id: int):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "Мероприятие")

    try:
        event, people, friends = await queries.get_event_page_data(request.user, event_id)
    except Event.DoesNotExist:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)

    if event.type == Event.Type.CLOSE and request.user not in people:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)

    if request.method == "POST":
        data = json.loads(request.body)
        if data["going"]:
            await queries.leave_event(request.user, event_id)
            await _invalidate_cache("event", "menu", "feed", "profile")
        else:
            return await _async_redirect(reverse("event_commit", kwargs={"event_id": event_id}))

    context["event"] = event
    context["user"] = request.user
    context["friends"] = friends
    context["people"] = people
    context["going"] = request.user in people
    context["address"] = event.address
    return await _async_render(request, "pages/main/event.html", context)


async def friends_page(request: HttpRequest):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "Друзья", reverse("friends"))
    friends_data = await queries.get_friends_page_data(request.user)
    context["friends"] = friends_data["friends"]
    context["friends_request_to_user"] = friends_data["friends_request_to_user"]
    context["friends_request_by_user"] = friends_data["friends_request_by_user"]
    context["friends_size"] = len(context["friends"])
    context["friends_request_to_user_size"] = len(context["friends_request_to_user"])
    context["friends_request_by_user_size"] = len(context["friends_request_by_user"])

    if request.method == "POST":
        await queries.apply_friends_action(request.user, request.POST)
        await _invalidate_cache(*FRIEND_CACHE_ROUTES)
        return await _async_redirect("/friends/")

    return await _async_render(request, "pages/friends/friends.html", context)


async def create_group_page(request: HttpRequest):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "Создание группы", reverse("groups"))
    form = CreateGroup(request.POST or None)

    if request.method == "POST" and await _async_form_is_valid(form):
        group = await queries.create_group_from_form(request.user, form)
        await _invalidate_cache(*GROUP_CACHE_ROUTES)
        return await _async_redirect(f"/groups/group/{group.id}")

    context["form"] = form
    return await _async_render(request, "pages/groups/create_group.html", context)


async def groups_page(request: HttpRequest):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "Группы", reverse("groups"))
    action = request.GET.get("action")
    if not action:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)
    if action not in {"watch", "invite"}:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)

    context.update(
        await queries.get_groups_page_data(
            request.user,
            action,
            request.GET.get("event_id"),
        )
    )
    return await _async_render(request, "pages/groups/user_groups.html", context)


async def group_page(request: HttpRequest, group_id: int):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, f"Группа №{group_id}", reverse("groups"))
    try:
        group, group_users, member_ids = await queries.get_group_page_data(request.user, group_id)
    except UserGroups.DoesNotExist:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)

    context["group"] = group
    context["users"] = group_users
    context["user"] = request.user

    if group.founder.id != request.user.id and group_id not in member_ids:
        return await _async_redirect("/groups/")

    if request.POST.get("del") == "del":
        await queries.delete_group(group)
        await _invalidate_cache(*GROUP_CACHE_ROUTES)
        return await _async_redirect("/groups/")
    if request.POST.get("del") == "user":
        await queries.remove_user_from_group(request.user, group)
        await _invalidate_cache(*GROUP_CACHE_ROUTES)
        return await _async_redirect("/groups/")

    return await _async_render(request, "pages/groups/group.html", context)


async def search_friends(request: HttpRequest):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "Поиск друзей", reverse("search_friends"))
    search_value = request.POST.get("search") if request.method == "POST" else None
    context["users"], context["users_size"] = await queries.get_search_friends_data(
        request.user,
        search_value,
    )
    context["form"] = SearchFriends(request.POST or None)

    friend_button = request.POST.get("friend_button")
    if friend_button:
        await queries.create_friend_request(request.user, friend_button)
        await _invalidate_cache(*FRIEND_CACHE_ROUTES)
        return await _async_redirect("/search_friends/")

    return await _async_render(request, "pages/friends/search_friends.html", context)


async def add_to_group_page(request: HttpRequest, group_id: int):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, f"Добавление в группу №{group_id}", reverse("groups"))
    search_value = request.POST.get("search") if request.method == "POST" else None

    try:
        group, users_to_invite, users_size = await queries.get_add_to_group_data(
            request.user,
            group_id,
            search_value,
        )
    except UserGroups.DoesNotExist:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)

    context["group"] = group
    context["group_id"] = group_id
    if group.founder.id != request.user.id:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)

    context["users"] = users_to_invite
    context["users_size"] = users_size
    context["form"] = SearchFriends(request.POST or None)

    invite = request.POST.get("invite")
    if invite:
        await queries.invite_user_to_group(request.user, group, invite)
        await _invalidate_cache(*GROUP_CACHE_ROUTES)
        return await _async_redirect(f"/groups/group/add_to_group/{group_id}")

    return await _async_render(request, "pages/groups/add_to_group.html", context)


async def remove_from_the_group_page(request: HttpRequest, group_id: int):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, f"Удаление из группы №{group_id}", reverse("groups"))
    search_value = request.POST.get("search") if request.method == "POST" else None

    try:
        group, users_to_remove, users_size = await queries.get_remove_from_group_data(
            request.user,
            group_id,
            search_value,
        )
    except UserGroups.DoesNotExist:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)

    context["group"] = group
    context["group_id"] = group_id
    if group.founder.id != request.user.id:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)

    context["users"] = users_to_remove
    context["users_size"] = users_size
    context["form"] = SearchFriends(request.POST or None)

    delete_id = request.POST.get("delete")
    if delete_id:
        await queries.remove_member_from_group(delete_id, group_id)
        await _invalidate_cache(*GROUP_CACHE_ROUTES)
        return await _async_redirect(f"/groups/group/remove_from_the_group/{group_id}")

    return await _async_render(request, "pages/groups/remove_from_the_group.html", context)


async def report_page(request: HttpRequest, report_id: int):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, f"Жалоба №{report_id}")
    try:
        report = await queries.get_report_page_data(request.user, report_id)
    except Report.DoesNotExist:
        return await _async_redirect(reverse("my_reports"))

    if report is None:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)

    context["report"] = report
    context["report_type"] = report.type
    context["id"] = report_id
    return await _async_render(request, "pages/reports/report.html", context)


async def create_report_page(request: HttpRequest):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "Создание жалобы")
    form = CreateReportForm(request.POST or None)

    if request.method == "POST" and await _async_form_is_valid(form):
        report = await queries.create_report(request.user, form)
        await _invalidate_cache(*REPORT_CACHE_ROUTES)
        return await _async_redirect(reverse("report", kwargs={"report_id": report.id}))

    context["form"] = form
    return await _async_render(request, "pages/reports/create_report.html", context)


async def my_reports_page(request: HttpRequest):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "Мои жалобы")
    reports, waiting_reports = await queries.get_my_reports_data(request.user)
    context["reports"] = reports
    context["reports_size"] = len(reports)
    context["waiting_reports"] = waiting_reports
    return await _async_render(request, "pages/reports/my_reports.html", context)


async def unverifed_reports_page(request: HttpRequest):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "Проверка жалоб")
    if not request.user.is_superuser:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)

    reports, reports_size = await queries.get_unverified_reports()
    context["reports"] = reports
    context["reports_size"] = reports_size
    return await _async_render(request, "pages/reports/unverifed_reports.html", context)


async def verify_report_page(request: HttpRequest, report_id: int):
    auth_redirect = await _require_login(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, f"Жалоба №{report_id}")
    if not request.user.is_superuser:
        return await _async_render(request, "pages/does_not_found.html", context, status=404)

    try:
        report = await queries.get_report_for_verification(report_id)
    except Report.DoesNotExist:
        return await _async_redirect("/reports/unverifed_reports")

    form = VerifyReportForm(request.POST or None)
    context["form"] = form
    context["report"] = report
    context["id"] = report_id

    if report.type == Report.Type.CLOSE:
        return await _async_redirect("/reports/unverifed_reports")

    if request.method == "POST" and await _async_form_is_valid(form):
        await queries.verify_report(report_id, form.cleaned_data["answer_text"])
        await _invalidate_cache(*REPORT_CACHE_ROUTES)
        return await _async_redirect("/reports/unverifed_reports")

    return await _async_render(request, "pages/reports/verify_report.html", context)
