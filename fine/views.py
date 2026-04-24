import json
from datetime import datetime
from functools import wraps
from urllib.parse import quote

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from django.template.defaultfilters import register
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib import messages

from fine.models import User, Event, Friends, UserGroups, Report, UserRecommendation
from fine.forms import EditProfile, RegistrationForm, CreateEvent, SearchFriends, CreateGroup, \
    VerifyReportForm, CreateReportForm
from fine.services import queries


def defense(func):
    """
    Декоратор при ошибке в функции редиректит на страницу ошибки
    """
    def wrapped(*args, **kwargs):
        from fine_project.settings import DEBUG
        if DEBUG:
            return func(*args, **kwargs)
        try:
            return func(*args, **kwargs)
        except Exception as err:
            print(err)
            return redirect(reverse("error"))

    return wrapped


@register.filter
def is_authenticated(menu_dict: dict, is_auth: bool):
    """
    Функция, которая возвращает нужный контекст для меню
    :param menu_dict: контекст меню из get_context
    :param is_auth: request.user.is_authenticated
    :return: нужный контекст
    """
    if is_auth:
        return menu_dict["authorized"]
    return menu_dict["unauthorized"]


@register.filter
def is_active(first_url: str, second_url: str):
    """
    Проверка на активную кнопку
    :param first_url: юрл кнопки
    :param second_url: юрл активной кнопки
    :return: active в класс кнопки
    """
    if first_url == second_url:
        return "active"
    return ""


@register.filter
def get_style(item: dict):
    """
    Функция для получения стиля для кнопки меню
    :param base_str: ""
    :param item: контекст кнопки
    :return: стиль для кнопки
    """
    return item.get("button-style", "btn-primary")


@register.filter
def get_theme(request: WSGIRequest):
    """
    получение темы пользователя
    """
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


def get_context(request: WSGIRequest = None, page_name="", active="") -> dict:
    """
    Функция для возвращения контекста меню

    :return: контекст меню
    """
    data = {
        'pagename': page_name,
        "active": active,
        "yandex_maps_api_key": settings.YANDEX_MAPS_API_KEY,
        "menu": {
            "left": {
                "unauthorized": [
                    {'url_name': '/', 'name': '\u0413\u043b\u0430\u0432\u043d\u0430\u044f \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430'},
                    {'url_name': '/menu/', 'name': '\u041c\u0435\u043d\u044e'},
                ],
            },
            "right": {
                "unauthorized": [
                    {'url_name': '/registration/', 'name': '\u0417\u0430\u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c\u0441\u044f'},
                    {'url_name': '/login/', 'name': '\u0412\u043e\u0439\u0442\u0438', "button-style": "btn-outline-primary"},
                ],
            },
        }
    }
    if not request:
        return data
    if request.user.is_authenticated:
        data["menu"]["left"]["authorized"] = [
            {'url_name': reverse('index'), 'name': '\u0413\u043b\u0430\u0432\u043d\u0430\u044f \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430'},
            {'url_name': reverse('menu'), 'name': '\u041c\u0435\u043d\u044e'},
            {'url_name': reverse('feed'), 'name': '\u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438'},
            {'url_name': reverse('friends'), 'name': '\u0414\u0440\u0443\u0437\u044c\u044f'},
            {'url_name': reverse('search_friends'), 'name': '\u041d\u0430\u0439\u0442\u0438 \u0434\u0440\u0443\u0433\u0430'},
        ]
        data["menu"]["right"]["authorized"] = [
            {'url_name': reverse('unverifed_reports') if request.user.is_superuser
            else reverse('my_reports'), 'name': '\u0416\u0430\u043b\u043e\u0431\u044b'},
            {'url_name': '/groups?action=watch', 'name': '\u0413\u0440\u0443\u043f\u043f\u044b'},
            {'url_name': reverse('profile', kwargs={'code': request.user.id}), 'name': '\u041f\u0440\u043e\u0444\u0438\u043b\u044c'},
            {'url_name': reverse('logout'), 'name': '\u0412\u044b\u0439\u0442\u0438', "button-style": "btn-outline-primary"},
        ]
    return data


@login_required
def theme_change(request: WSGIRequest):
    """
    Меняет тему пользователя
    """
    if request.user.theme == "white":
        User.objects.filter(id=request.user.id).update(theme="dark")
    if request.user.theme == "dark":
        User.objects.filter(id=request.user.id).update(theme="white")
    return JsonResponse({"details": "ok"})


def index_page(request: WSGIRequest):
    """
    Главная страница сайта
    """
    context = get_context(request, "\u0413\u043b\u0430\u0432\u043d\u0430\u044f", reverse("index"))
    context["events"] = list(Event.objects.filter(type=1))[: 3]
    return render(request, 'pages/start/index.html', context)


def error_page(request: WSGIRequest):
    """
    Страница ошибки
    """
    context = get_context(request, "\u041e\u0448\u0438\u0431\u043a\u0430")
    return render(request, 'pages/does_not_found.html', context)
def menu_page(request: WSGIRequest):
    """
    Меню с мероприятиями
    """
    context = get_context(request, "Меню", reverse("menu"))
    context["events"] = Event.objects.filter(type=1, status=True)
    context['user'] = request.user
    if request.user.is_authenticated:
        context["private_events"] = request.user.event_members.filter(type=0, status=True)

    if request.method == 'POST':
        if request.POST.get('entertainment_type') == '-1':
            context["events"] = Event.objects.filter(type=1, status=True)
            if request.user.is_authenticated:
                context["private_events"] = request.user.event_members.filter(type=0,
                                                                          status=True)
        else:
            context["events"] = Event.objects.filter(type=1, status=True,
                                                     entertainment_type=request.POST.get('entertainment_type'))
            if request.user.is_authenticated:
                context["private_events"] = request.user.event_members.filter(type=0, status=True,
                                                                          entertainment_type=request.POST.get(
                                                                              'entertainment_type'))

    return render(request, 'pages/start/menu.html', context)


@defense
@login_required
def feed_page(request: WSGIRequest):
    """
    Персональная лента рекомендаций мероприятий.
    """
    context = get_context(request, "Рекомендации", reverse("feed"))

    recommendations_qs = UserRecommendation.objects.filter(user=request.user)
    if not recommendations_qs.exists():
        generate_for_user(request.user)
        recommendations_qs = UserRecommendation.objects.filter(user=request.user)

    recommendations = recommendations_qs.select_related("event", "event__author").order_by("rank")

    if request.method == 'POST' and request.POST.get('entertainment_type') != '-1':
        recommendations = recommendations.filter(
            event__entertainment_type=request.POST.get('entertainment_type')
        )

    context["recommendations"] = recommendations
    context["recommendations_size"] = recommendations.count()
    return render(request, 'pages/main/feed.html', context)


@defense
def registration_page(request: WSGIRequest):
    """
    Страница регистрации пользователя.
    """
    context = get_context(request, "Регистрация", reverse("register"))
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = User(username=form.cleaned_data['username'], password=make_password(form.cleaned_data['password2']),
                        first_name=form.cleaned_data['first_name'], last_name=form.cleaned_data['last_name'],
                        email=form.cleaned_data['email'])
            user.save()
            return redirect('/')
        context['errors'] = form.errors
    else:
        form = RegistrationForm()
    context['form'] = form

    return render(request, 'registration/register.html', context)


@defense
@login_required
def event_create_page(request: WSGIRequest):
    """
    Страница с созданием мероприятия
    """
    context = get_context(request, "Создание мероприятия")
    context['today'] = str(datetime.today().date())
    if request.method == 'POST':
        form = CreateEvent(request.POST)
        if form.is_valid():
            if form.cleaned_data['start_day'] <= form.cleaned_data['finish_day']:
                event = Event(name=form.cleaned_data['name'], type=form.cleaned_data['type'],
                              address=form.cleaned_data['address'], start_day=form.cleaned_data['start_day'],
                              finish_day=form.cleaned_data['finish_day'], description=form.cleaned_data['description'],
                              author=request.user, entertainment_type=form.cleaned_data['entertainment_type'])
                event.save()
                return redirect(reverse('event_commit', kwargs={"event_id": event.id}))
            messages.add_message(request, messages.ERROR, "Дата окончания не может быть раньше даты начала.")
    else:
        form = CreateEvent()
    context['form'] = form
    return render(request, 'pages/event/create.html', context)


@defense
@login_required
def event_edit_page(request: WSGIRequest, event_id: int):
    """
    Cтраница изменения мероприятия

    :param event_id: Event ID
    :type event_id: int
    """
    context = get_context(request, "Редактирование мероприятия")
    context["event_id"] = event_id
    event = Event.objects.get(pk=event_id)
    form = CreateEvent(instance=event)
    if request.method == 'POST':
        form = CreateEvent(request.POST, instance=event)
        if form.is_valid():
            form.save()
    context['form'] = form
    return render(request, 'pages/event/edit.html', context)


@defense
@login_required
def commit_event_page(request, event_id):
    """
    Страница с добавлением пользователя на мероприятие

    :param event_id: Event ID
    :type event_id: int
    """
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        return redirect(reverse('event', kwargs={"event_id": event_id}))

    request.user.event_members.add(event)

    return redirect(reverse('event', kwargs={"event_id": event_id}))


@defense
@login_required
def commit_event_group_page(request, event_id, group_id):
    """
    Страница с добавлением группы пользователей на мероприятие

    :param event_id: Event ID
    :type event_id: int
    :param group_id: Group ID
    :type group_id: int
    """
    event = Event.objects.get(pk=event_id)
    group = UserGroups.objects.get(id=group_id)
    members = group.members.all()

    if request.user != event.author or request.user != group.founder:
        return redirect('/')

    for user in members:
        user.event_members.add(event)
        user.save()

    return redirect(reverse('event', kwargs={"event_id": event_id}))


def friends_for_profile_view_page_algo(request: WSGIRequest, code: int):
    """
    Набор алгоритмов для страницы профиля.

    :param request: Параметр запроса для POST-обработки.
    :type request: :class: 'django.http.HttpRequest'
    :param code: ID пользователя.
    :type event_id: int
    """
    if request.POST.get('button') == 'friend_button':
        Friends.objects.create(from_user=request.user, to_user=User.objects.get(id=code), waiting=True)
    elif request.POST.get('button') == 'del_request':
        Friends.objects.get(from_user=request.user, to_user=User.objects.get(id=code)).delete()
    elif request.POST.get('button') == 'del_friend':
        Friends.objects.get(from_user=request.user, to_user=User.objects.get(id=code)).delete()
        Friends.objects.get(from_user=User.objects.get(id=code), to_user=request.user).delete()
    elif request.POST.get('button') == 'acp_friend':
        Friends.objects.create(to_user=User.objects.get(id=code), from_user=request.user, waiting=False)
        Friends.objects.filter(id=Friends.objects.get(to_user=request.user, from_user=code).id).update(waiting=False)


@defense
def profile_view_page(request: WSGIRequest, code: int):
    """
    Страница профиля пользователя.

    :param code: ID пользователя
    :type code: int
    """
    context = get_context(request, "Профиль", reverse("profile", kwargs={'code': code}))
    try:
        context['user'] = User.objects.get(id=code)
        context['events'] = list(context['user'].event_members.filter(type=1))
        context['my_events'] = list(Event.objects.filter(author=context['user'], type=1))
    except User.DoesNotExist as user_does_not_exist:
        context['events'] = None
        context['my_events'] = None
        raise Http404 from user_does_not_exist
    if request.user.is_authenticated:
        try:
            friend = Friends.objects.get(from_user=request.user, to_user=User.objects.get(id=code))
            context['waiting_friend'] = friend.waiting
        except Friends.DoesNotExist:
            context['already_friend'] = False
        try:
            Friends.objects.get(from_user=User.objects.get(id=code), to_user=request.user, waiting=True)
            context['have_request'] = True
        except Friends.DoesNotExist:
            context['have_request'] = False
    if request.method == 'POST':
        friends_for_profile_view_page_algo(request, code)
        return redirect('/profile/' + str(code))

    return render(request, 'pages/profile/view.html', context)


@defense
@login_required
def edit_page(request: WSGIRequest):
    """
    Страница редактирования основной информации профиля.
    """
    context = get_context(request, "Редактирование профиля", reverse("profile", kwargs={'code': request.user.id}))

    cur_user = User.objects.get(username=request.user.username)
    form = EditProfile(instance=cur_user)

    if request.method == 'POST':
        form = EditProfile(request.POST, request.FILES, instance=cur_user)
        if form.is_valid():
            form.save()
        return redirect('/profile/' + str(request.user.id))
    context['form'] = form

    return render(request, 'pages/profile/edit_about.html', context)


def friends_algo(request: WSGIRequest):
    """
    Набор алгоритмов для страницы с дрзьями.
    :param request: Параметр запроса для POST-обработки
    """
    if request.POST.get('cancel_to_request'):
        Friends.objects.get(id=request.POST.get('cancel_to_request')).delete()

    if request.POST.get('accept_from_request'):
        friend = Friends.objects.get(id=request.POST.get('accept_from_request'))
        Friends.objects.create(to_user=friend.from_user, from_user=request.user, waiting=False)
        Friends.objects.filter(id=request.POST.get('accept_from_request')).update(waiting=False)

    if request.POST.get('cancel_from_request'):
        Friends.objects.get(id=request.POST.get('cancel_from_request')).delete()

    if request.POST.get('del_friend'):
        friend = Friends.objects.get(id=request.POST.get('del_friend'))
        Friends.objects.get(to_user=friend.to_user, from_user=friend.from_user).delete()
        Friends.objects.get(to_user=friend.from_user, from_user=friend.to_user).delete()


def get_user(received_object: Friends) -> User:
    """
    получает юзера из RegistrationEvents/Friends
    :param received_object: объект RegistrationEvents/Friends
    :return: объект User
    """
    if isinstance(received_object, Friends):
        return received_object.from_user
    return received_object.user


@defense
@login_required
def event_page(request: WSGIRequest, event_id: int):
    """

    :param request:
    :param event_id:
    :return:
    """
    context = get_context(request, "Мероприятие")
    try:
        event: Event = Event.objects.get(id=event_id)
        people: list[User] = User.objects.filter(event_members__id=event_id).all()

        if event.type == 0 and request.user not in people:
            return render(request, 'pages/does_not_found.html', context)

        if request.method == 'POST':
            data = json.loads(request.body)
            if data["going"]:
                request.user.event_members.remove(event_id)
            else:
                return redirect(reverse('event_commit', kwargs={"event_id": event_id}))

        friends: list[Friends] = Friends.objects.filter(to_user=request.user, waiting=False).all()
        friends: list[User] = list(map(get_user, friends))
        friends_set = set(friends)
        people_set = set(people)

        friends = list(friends_set.intersection(people_set))

        context['event'] = event
        context['user'] = request.user
        context['friends'] = friends
        context['people'] = people
        context['going'] = request.user in people
        context['address'] = event.address
    except IndexError:
        return render(request, 'pages/does_not_found.html', context)
    return render(request, 'pages/main/event.html', context)


def get_friends(user_id: int):
    """
    Функция, возвращающая список друзей пользователя.
    :param user_id: ID пользователя
    :return: Список друзей
    """
    return Friends.objects.filter(from_user=User.objects.get(id=user_id).id, waiting=False)


@defense
@login_required
def friends_page(request: WSGIRequest):
    """
    Страница с друзьями пользователя
    """

    context = get_context(request, "Друзья", reverse("friends"))
    context["friends"] = list(Friends.objects.filter(to_user=request.user, waiting=False))
    context["friends_request_to_user"] = list(Friends.objects.filter(to_user=request.user, waiting=True))
    context["friends_request_by_user"] = list(Friends.objects.filter(from_user=request.user, waiting=True))
    context['friends_size'] = len(context['friends'])
    context['friends_request_to_user_size'] = len(context['friends_request_to_user'])
    context['friends_request_by_user_size'] = len(context['friends_request_by_user'])

    if request.method == 'POST':
        friends_algo(request)

        return redirect('/friends/')

    return render(request, 'pages/friends/friends.html', context)


@defense
@login_required
def create_group_page(request):
    """
    Страница с созданием пользовательской группы
    """
    context = get_context(request, "Создание группы", reverse('groups'))

    if request.method == 'POST':
        form = CreateGroup(request.POST)
        if form.is_valid():
            group = UserGroups.objects.create(title=form.cleaned_data['title'],
                                              description=form.cleaned_data['description'],
                                              founder=request.user)

            return redirect('/groups/group/' + str(group.id))
    else:
        form = CreateGroup()
    context['form'] = form

    return render(request, 'pages/groups/create_group.html', context)


@defense
@login_required
def groups_page(request):
    """
    Страница со всеми пользовательскими группами
    """
    context = get_context(request, "Группы", reverse('groups'))
    if request.method == 'GET':
        if len(request.GET) == 0:
            return render(request, 'pages/does_not_found.html', context)
        if request.GET['action'] == 'watch':
            context['buttons'] = 'Информация'
            context['action'] = request.GET['action']
            context['groups'] = request.user.members.all()
        elif request.GET['action'] == 'invite':
            context['buttons'] = 'Добавить'
            context['action'] = request.GET['action']
            context['event_id'] = request.GET['event_id']
        else:
            return render(request, 'pages/does_not_found.html', context)

    context['my_groups'] = UserGroups.objects.filter(founder=request.user)

    return render(request, 'pages/groups/user_groups.html', context)


@defense
@login_required
def group_page(request, group_id: int):
    """
    Страница с пользовательской группой
    """
    context = get_context(request, 'Группа №' + str(group_id), reverse('groups'))
    context['group'] = UserGroups.objects.get(id=group_id)
    context['users'] = User.objects.filter(members__id=group_id)
    context['user'] = request.user

    if UserGroups.objects.get(id=group_id).founder.id is not request.user.id and \
            group_id not in request.user.members.all().values_list('id', flat=True):
        return redirect('/groups/')

    if request.POST.get('del') == 'del':
        context['group'].delete()
        return redirect('/groups/')
    if request.POST.get('del') == 'user':
        context['user'].members.remove(context['group'])
        return redirect('/groups/')

    return render(request, 'pages/groups/group.html', context)


class Search:
    """
    Класс для осуществления поиска
    """

    def __init__(self, req):
        """
        Конструктор
        """
        self.form = SearchFriends()
        self.request = req

    def reload(self, req):
        """
        Изменение параметра
        """
        self.request = req

    def search(self):
        """
        Поиск
        """
        self.form = SearchFriends(self.request.POST)
        if self.form.is_valid():
            search = self.form.cleaned_data['search']

            users_search = (User.objects.filter(first_name__icontains=search) |
                            User.objects.filter(last_name__icontains=search) |
                            User.objects.filter(username__icontains=search))
            return users_search
        return User.objects.all()


class GetFriendsGroup:
    """
    Класс для получения группы друзей
    """

    def __init__(self, req):
        """
        Конструктор
        """
        self.request = req

    def get_friends_id(self):
        """
        Возвращает ID всех друзей
        """
        friends = get_friends(self.get_my_user_id())
        friends_id = [friend.to_user_id for friend in friends]
        return friends_id

    def get_friends_request_id(self):
        """
        Возвращает ID запрашиваемых друзей
        """
        friends = Friends.objects.filter(from_user=self.get_my_user_id())
        friends_to_id = [friend.to_user_id for friend in friends]
        friends = Friends.objects.filter(to_user=self.get_my_user_id())
        friends_from_id = [friend.from_user_id for friend in friends]
        friends_id = friends_to_id + friends_from_id
        return friends_id

    @staticmethod
    def get_friends_group_id(group_id):
        """
        Возвращает ID группы друзей
        """
        friends_group = User.objects.filter(members__id=group_id)
        friends_group_id = [friend.id for friend in friends_group]
        return friends_group_id

    def get_my_user_id(self):
        """
        Возвращает ID пользователя
        """
        return self.request.user.id


@defense
@login_required
def search_friends(request):
    """
    Страница для поиска друзей
    """
    context = get_context(request, "Поиск друзей", reverse("search_friends"))
    get_friends_group = GetFriendsGroup(request)
    find = Search(request)
    users_friends = User.objects.exclude(id__in=get_friends_group.get_friends_request_id())
    my_user = User.objects.exclude(id=get_friends_group.get_my_user_id())
    context['users'] = User.objects.all() & users_friends & my_user
    context['users_size'] = len(context['users'])
    if request.method == 'POST':
        find.reload(request)
        users = find.search() & my_user & users_friends
        context['users'] = users
        context['users_size'] = len(users)
    context['form'] = find.form
    if request.POST.get('friend_button'):
        Friends.objects.create(from_user=request.user,
                               to_user=User.objects.get(id=request.POST.get('friend_button')), waiting=True)
        return redirect('/search_friends/')

    return render(request, 'pages/friends/search_friends.html', context)


@defense
@login_required
def add_to_group_page(request, group_id: int):
    """
    Страница с добавлением пользователей в группу
    """
    context = get_context(request, 'Добавление в группу №' + str(group_id), reverse('groups'))
    context['group'] = UserGroups.objects.get(id=group_id)
    context['group_id'] = group_id

    if UserGroups.objects.get(id=group_id).founder.id is not request.user.id:
        return render(request, 'pages/does_not_found.html', context)

    get_friends_group = GetFriendsGroup(request)

    users_friends_all = User.objects.filter(id__in=get_friends_group.get_friends_id())
    users_friends = User.objects.exclude(id__in=get_friends_group.get_friends_group_id(group_id))

    my_user = User.objects.exclude(id=get_friends_group.get_my_user_id())

    users_to_invite = my_user & users_friends_all & users_friends
    context['users'] = users_to_invite
    context['users_size'] = len(context['users'])
    find = Search(request)

    if request.method == 'POST':
        find.reload(request)
        context['users'] = find.search() & users_to_invite
        context['users_size'] = len(context['users'])
    context['form'] = find.form

    if request.method == 'POST':
        if request.POST.get('invite'):
            invented = Friends.objects.get(from_user_id=request.POST.get('invite'), to_user=request.user)
            invented = User.objects.get(id=invented.from_user_id)
            invented.members.add(context['group'])
            return redirect('/groups/group/add_to_group/' + str(context['group_id']))

    return render(request, 'pages/groups/add_to_group.html', context)


@defense
@login_required
def remove_from_the_group_page(request, group_id: int):
    """
    Страница с удалением пользователей из группы
    """
    context = get_context(request, 'Удаление из группы №' + str(group_id), reverse('groups'))
    context['group'] = UserGroups.objects.get(id=group_id)
    context['group_id'] = group_id

    if UserGroups.objects.get(id=group_id).founder.id is not request.user.id:
        return render(request, 'pages/does_not_found.html', context)

    get_friends_group = GetFriendsGroup(request)

    users_friends = User.objects.filter(id__in=get_friends_group.get_friends_group_id(group_id))
    my_user = User.objects.exclude(id=get_friends_group.get_my_user_id())

    users_to_invite = my_user & users_friends

    context['users'] = users_to_invite
    context['users_size'] = len(context['users'])
    find = Search(request)
    if request.method == 'POST':
        find.reload(request)
        context['users'] = find.search() & users_to_invite
        context['users_size'] = len(context['users'])
    context['form'] = find.form

    if request.method == 'POST':
        if request.POST.get('delete'):
            user_to_delete = User.objects.get(id=request.POST.get('delete'))
            user_to_delete.members.remove(group_id)
            return redirect('/groups/group/remove_from_the_group/' + str(context['group_id']))

    return render(request, 'pages/groups/remove_from_the_group.html', context)


@defense
@login_required
def report_page(request, report_id: int):
    """
    Страница с репортом
    """
    context = get_context(request, "Жалоба №" + str(report_id))

    try:
        if Report.objects.get(id=report_id).author != request.user:
            return render(request, 'pages/does_not_found.html', context)
        context['report'] = Report.objects.get(id=report_id)
        context['report_type'] = context['report'].type
        context['id'] = report_id
    except Report.DoesNotExist:
        return redirect('my_profile/my_reports/')

    return render(request, 'pages/reports/report.html', context)


@defense
@login_required
def create_report_page(request):
    """
    Страница с созданием репорта
    """
    context = get_context(request, 'Создание жалобы')
    context['form'] = CreateReportForm(request.POST) if request.method == 'POST' else CreateReportForm()

    if request.method == 'POST':
        if context['form'].is_valid():
            rep = Report.objects.create(author=request.user,
                                        report_text=context['form'].cleaned_data['report_text'],
                                        type=1, created_at=datetime.now())
            return redirect(reverse('report', kwargs={"report_id": rep.id}))

    return render(request, 'pages/reports/create_report.html', context)


@defense
@login_required
def my_reports_page(request):
    """
    Репорты пользователя
    """
    context = get_context(request, 'Мои жалобы')

    try:
        context['reports'] = Report.objects.filter(author=request.user)
        context['reports_size'] = len(context['reports'])
        context['waiting_reports'] = len(Report.objects.filter(author=request.user, type=2))
    except Report.DoesNotExist:
        context['reports_size'] = 0

    return render(request, 'pages/reports/my_reports.html', context)


@defense
@login_required
def unverifed_reports_page(request):
    """
    Страница с репортами, на которые не дали ответы
    """
    context = get_context(request, 'Проверка жалоб')

    if not request.user.is_superuser:
        return render(request, 'pages/does_not_found.html', context)

    try:
        context['reports'] = Report.objects.filter(type=1)
        context['reports_size'] = len(context['reports'])
    except Report.DoesNotExist:
        context['reports_size'] = 0

    return render(request, 'pages/reports/unverifed_reports.html', context)


@defense
@login_required
def verify_report_page(request, report_id):
    """
    Страница с ответом на репорт
    """
    context = get_context(request, "Жалоба №" + str(report_id))

    if not request.user.is_superuser:
        return render(request, 'pages/does_not_found.html', context)

    context['form'] = VerifyReportForm(request.POST) if request.method == 'POST' else VerifyReportForm()

    context['report'] = Report.objects.get(id=report_id)
    context['id'] = report_id

    if context['report'].type == 2:
        return redirect('/reports/unverifed_reports')

    if request.method == 'POST':
        if context['form'].is_valid():
            Report.objects.filter(id=report_id).update(closed_at=datetime.now(),
                                                       answer_text=context['form'].cleaned_data['answer_text'], type=2)
            return redirect('/reports/unverifed_reports')

    return render(request, 'pages/reports/verify_report.html', context)


def _make_async_view(sync_view):
    @wraps(sync_view)
    async def async_view(*args, **kwargs):
        return await sync_to_async(sync_view, thread_sensitive=True)(*args, **kwargs)

    return async_view


async def _async_render(request, template_name, context):
    return await sync_to_async(render, thread_sensitive=True)(request, template_name, context)


async def _async_redirect(*args, **kwargs):
    return await sync_to_async(redirect, thread_sensitive=True)(*args, **kwargs)


async def _async_form_is_valid(form):
    return await sync_to_async(form.is_valid, thread_sensitive=True)()


async def _async_form_save(form):
    return await sync_to_async(form.save, thread_sensitive=True)()


async def _async_save(instance, **kwargs):
    return await sync_to_async(instance.save, thread_sensitive=True)(**kwargs)


async def _async_delete(instance):
    return await sync_to_async(instance.delete, thread_sensitive=True)()


async def _async_update(queryset, **kwargs):
    return await queryset.aupdate(**kwargs)


async def _async_add_m2m(manager, *objects):
    return await sync_to_async(manager.add, thread_sensitive=True)(*objects)


async def _async_remove_m2m(manager, *objects):
    return await sync_to_async(manager.remove, thread_sensitive=True)(*objects)


async def _async_list(queryset):
    return [item async for item in queryset]


async def _async_first(queryset):
    return await queryset.afirst()


async def _async_login_required(request):
    user = await sync_to_async(queries.resolve_request_user, thread_sensitive=True)(request)
    if user.is_authenticated:
        return None
    next_url = quote(request.get_full_path(), safe="/?=&")
    return await _async_redirect(f"{settings.LOGIN_URL}?next={next_url}")


def _resolve_request_user(request):
    user = request.user
    user.is_authenticated
    request.user = user
    return user


async def _friends_for_profile_view_page_algo_async(request: WSGIRequest, code: int):
    target_user = await User.objects.aget(id=code)
    button = request.POST.get('button')
    if button == 'friend_button':
        await Friends.objects.acreate(from_user=request.user, to_user=target_user, waiting=True)
    elif button == 'del_request':
        relation = await Friends.objects.aget(from_user=request.user, to_user=target_user)
        await _async_delete(relation)
    elif button == 'del_friend':
        relation = await Friends.objects.aget(from_user=request.user, to_user=target_user)
        await _async_delete(relation)
        обратная_связь = await Friends.objects.aget(from_user=target_user, to_user=request.user)
        await обратная_связь.adelete()
    elif button == 'acp_friend':
        await Friends.objects.acreate(to_user=target_user, from_user=request.user, waiting=False)
        incoming = await Friends.objects.aget(to_user=request.user, from_user=code)
        await Friends.objects.filter(id=incoming.id).aupdate(waiting=False)


async def _friends_algo_async(request: WSGIRequest):
    cancel_to_request = request.POST.get('cancel_to_request')
    if cancel_to_request:
        relation = await Friends.objects.aget(id=cancel_to_request)
        await _async_delete(relation)

    accept_from_request = request.POST.get('accept_from_request')
    if accept_from_request:
        friend = await Friends.objects.aget(id=accept_from_request)
        await Friends.objects.acreate(to_user=friend.from_user, from_user=request.user, waiting=False)
        await Friends.objects.filter(id=accept_from_request).aupdate(waiting=False)

    cancel_from_request = request.POST.get('cancel_from_request')
    if cancel_from_request:
        relation = await Friends.objects.aget(id=cancel_from_request)
        await _async_delete(relation)

    del_friend = request.POST.get('del_friend')
    if del_friend:
        friend = await Friends.objects.aget(id=del_friend)
        first = await Friends.objects.aget(to_user=friend.to_user, from_user=friend.from_user)
        second = await Friends.objects.aget(to_user=friend.from_user, from_user=friend.to_user)
        await _async_delete(first)
        await _async_delete(second)


async def _search_users_async(search_value):
    if search_value:
        return (
            User.objects.filter(first_name__icontains=search_value)
            | User.objects.filter(last_name__icontains=search_value)
            | User.objects.filter(username__icontains=search_value)
        )
    return User.objects.all()


async def _friends_for_profile_view_page_algo_async(request: WSGIRequest, code: int):
    target_user = await User.objects.aget(id=code)
    button = request.POST.get('button')
    if button == 'friend_button':
        await Friends.objects.acreate(from_user=request.user, to_user=target_user, waiting=True)
    elif button == 'del_request':
        relation = await Friends.objects.aget(from_user=request.user, to_user=target_user)
        await _async_delete(relation)
    elif button == 'del_friend':
        relation = await Friends.objects.aget(from_user=request.user, to_user=target_user)
        await _async_delete(relation)
        reverse_relation = await Friends.objects.aget(from_user=target_user, to_user=request.user)
        await _async_delete(reverse_relation)
    elif button == 'acp_friend':
        await Friends.objects.acreate(to_user=target_user, from_user=request.user, waiting=False)
        incoming = await Friends.objects.aget(to_user=request.user, from_user=code)
        await Friends.objects.filter(id=incoming.id).aupdate(waiting=False)


async def _friend_request_ids_async(user_id: int):
    outgoing = [
        friend.to_user_id
        async for friend in Friends.objects.filter(from_user=user_id)
    ]
    incoming = [
        friend.from_user_id
        async for friend in Friends.objects.filter(to_user=user_id)
    ]
    return outgoing + incoming


async def _group_member_ids_async(group_id: int):
    return [friend.id async for friend in User.objects.filter(members__id=group_id)]


async def _friend_ids_async(user_id: int):
    return [
        friend.to_user_id
        async for friend in Friends.objects.filter(from_user=user_id, waiting=False)
    ]


async def theme_change(request: WSGIRequest):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    await queries.update_user_theme(request.user)
    return JsonResponse({"details": "ok"})


async def index_page(request: WSGIRequest):
    await sync_to_async(queries.resolve_request_user, thread_sensitive=True)(request)
    context = get_context(request, "\u0413\u043b\u0430\u0432\u043d\u0430\u044f", reverse("index"))
    context["events"] = await queries.get_index_events()
    return await _async_render(request, 'pages/start/index.html', context)


async def error_page(request: WSGIRequest):
    await sync_to_async(queries.resolve_request_user, thread_sensitive=True)(request)
    context = get_context(request, "\u041e\u0448\u0438\u0431\u043a\u0430")
    return await _async_render(request, 'pages/does_not_found.html', context)


async def menu_page(request: WSGIRequest):
    await sync_to_async(queries.resolve_request_user, thread_sensitive=True)(request)
    context = get_context(request, "\u041c\u0435\u043d\u044e", reverse("menu"))
    entertainment_type = request.POST.get('entertainment_type') if request.method == 'POST' else None

    events_qs, private_events_qs = await queries.get_menu_querysets(
        request.user,
        entertainment_type,
    )

    context["events"] = events_qs
    context["events_map_data"] = await queries.serialize_events_for_map(events_qs)
    context['user'] = request.user
    if request.user.is_authenticated:
        context["private_events"] = private_events_qs

    return await _async_render(request, 'pages/start/menu.html', context)


async def feed_page(request: WSGIRequest):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438", reverse("feed"))
    recommendations_qs = await queries.get_recommendations_queryset(
        request.user,
        request.POST.get('entertainment_type') if request.method == 'POST' else None,
    )
    context["recommendations"] = recommendations_qs
    context["recommendations_size"] = await recommendations_qs.acount()
    return await _async_render(request, 'pages/main/feed.html', context)


async def registration_page(request: WSGIRequest):
    await sync_to_async(queries.resolve_request_user, thread_sensitive=True)(request)
    context = get_context(request, "\u0420\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044f", reverse("register"))
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if await _async_form_is_valid(form):
            await User.objects.acreate(
                username=form.cleaned_data['username'],
                password=make_password(form.cleaned_data['password2']),
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
            )
            return await _async_redirect('/')
        context['errors'] = form.errors
    else:
        form = RegistrationForm()
    context['form'] = form
    return await _async_render(request, 'registration/register.html', context)


async def event_create_page(request: WSGIRequest):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0421\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u043c\u0435\u0440\u043e\u043f\u0440\u0438\u044f\u0442\u0438\u044f")
    context['today'] = str(datetime.today().date())
    if request.method == 'POST':
        form = CreateEvent(request.POST)
        if await _async_form_is_valid(form):
            if form.cleaned_data['start_day'] <= form.cleaned_data['finish_day']:
                event = await queries.create_event_from_form(request.user, form)
                return await _async_redirect(reverse('event_commit', kwargs={"event_id": event.id}))
            await sync_to_async(messages.add_message, thread_sensitive=True)(
                request,
                messages.ERROR,
                "\u0414\u0430\u0442\u0430 \u043e\u043a\u043e\u043d\u0447\u0430\u043d\u0438\u044f \u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c \u0440\u0430\u043d\u044c\u0448\u0435 \u0434\u0430\u0442\u044b \u043d\u0430\u0447\u0430\u043b\u0430."
            )
        context['errors'] = form.errors
    else:
        form = CreateEvent()
    context['form'] = form
    return await _async_render(request, 'pages/event/create.html', context)


async def event_edit_page(request: WSGIRequest, event_id: int):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0420\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u043c\u0435\u0440\u043e\u043f\u0440\u0438\u044f\u0442\u0438\u044f")
    context["event_id"] = event_id
    event = await queries.get_event_for_edit(event_id)
    context["event"] = event
    form = CreateEvent(instance=event)
    if request.method == 'POST':
        form = CreateEvent(request.POST, instance=event)
        if await _async_form_is_valid(form):
            await _async_form_save(form)
    context['form'] = form
    return await _async_render(request, 'pages/event/edit.html', context)


async def commit_event_page(request, event_id):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    try:
        event = await queries.add_user_to_event(request.user, event_id)
    except Event.DoesNotExist:
        return await _async_redirect(reverse('event', kwargs={"event_id": event_id}))
    return await _async_redirect(reverse('event', kwargs={"event_id": event_id}))


async def commit_event_group_page(request, event_id, group_id):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    event = await queries.add_group_members_to_event(request.user, event_id, group_id)
    if event is None:
        return await _async_redirect('/')

    return await _async_redirect(reverse('event', kwargs={"event_id": event_id}))


async def profile_view_page(request: WSGIRequest, code: int):
    await sync_to_async(queries.resolve_request_user, thread_sensitive=True)(request)
    context = get_context(request, "\u041f\u0440\u043e\u0444\u0438\u043b\u044c", reverse("profile", kwargs={'code': code}))
    try:
        profile_data = await queries.get_profile_page_data(request.user, code)
        context['user'] = profile_data['user']
        context['events'] = profile_data['events']
        context['my_events'] = profile_data['my_events']
    except User.DoesNotExist as user_does_not_exist:
        context['events'] = None
        context['my_events'] = None
        raise Http404 from user_does_not_exist

    if profile_data['waiting_friend'] is not None:
        context['waiting_friend'] = profile_data['waiting_friend']
    if profile_data['already_friend'] is not None:
        context['already_friend'] = profile_data['already_friend']
    context['have_request'] = profile_data['have_request']

    if request.method == 'POST':
        await queries.apply_profile_friend_action(request.user, code, request.POST.get('button'))
        return await _async_redirect('/profile/' + str(code))

    return await _async_render(request, 'pages/profile/view.html', context)


async def edit_page(request: WSGIRequest):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0420\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u043f\u0440\u043e\u0444\u0438\u043b\u044f", reverse("profile", kwargs={'code': request.user.id}))
    cur_user = await User.objects.aget(username=request.user.username)
    form = EditProfile(instance=cur_user)

    if request.method == 'POST':
        form = EditProfile(request.POST, request.FILES, instance=cur_user)
        if await _async_form_is_valid(form):
            await _async_form_save(form)
        return await _async_redirect('/profile/' + str(request.user.id))
    context['form'] = form
    return await _async_render(request, 'pages/profile/edit_about.html', context)


async def event_page(request: WSGIRequest, event_id: int):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u041c\u0435\u0440\u043e\u043f\u0440\u0438\u044f\u0442\u0438\u0435")
    try:
        event, people, friends = await queries.get_event_page_data(request.user, event_id)

        if event.type == 0 and request.user not in people:
            return await _async_render(request, 'pages/does_not_found.html', context)

        if request.method == 'POST':
            data = json.loads(request.body)
            if data["going"]:
                await queries.leave_event(request.user, event_id)
            else:
                return await _async_redirect(reverse('event_commit', kwargs={"event_id": event_id}))

        context['event'] = event
        context['user'] = request.user
        context['friends'] = friends
        context['people'] = people
        context['going'] = request.user in people
        context['address'] = event.address
    except IndexError:
        return await _async_render(request, 'pages/does_not_found.html', context)
    return await _async_render(request, 'pages/main/event.html', context)


async def friends_page(request: WSGIRequest):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0414\u0440\u0443\u0437\u044c\u044f", reverse("friends"))
    friends_data = await queries.get_friends_page_data(request.user)
    context["friends"] = friends_data["friends"]
    context["friends_request_to_user"] = friends_data["friends_request_to_user"]
    context["friends_request_by_user"] = friends_data["friends_request_by_user"]
    context['friends_size'] = len(context['friends'])
    context['friends_request_to_user_size'] = len(context['friends_request_to_user'])
    context['friends_request_by_user_size'] = len(context['friends_request_by_user'])

    if request.method == 'POST':
        await queries.apply_friends_action(request.user, request.POST)
        return await _async_redirect('/friends/')

    return await _async_render(request, 'pages/friends/friends.html', context)


async def create_group_page(request):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0421\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u0433\u0440\u0443\u043f\u043f\u044b", reverse('groups'))
    if request.method == 'POST':
        form = CreateGroup(request.POST)
        if await _async_form_is_valid(form):
            group = await queries.create_group_from_form(request.user, form)
            return await _async_redirect('/groups/group/' + str(group.id))
    else:
        form = CreateGroup()
    context['form'] = form
    return await _async_render(request, 'pages/groups/create_group.html', context)


async def groups_page(request):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0413\u0440\u0443\u043f\u043f\u044b", reverse('groups'))
    if request.method == 'GET':
        if len(request.GET) == 0:
            return await _async_render(request, 'pages/does_not_found.html', context)
        if request.GET['action'] not in {'watch', 'invite'}:
            return await _async_render(request, 'pages/does_not_found.html', context)
        context.update(
            await queries.get_groups_page_data(
                request.user,
                request.GET['action'],
                request.GET.get('event_id'),
            )
        )
    return await _async_render(request, 'pages/groups/user_groups.html', context)


async def group_page(request, group_id: int):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0413\u0440\u0443\u043f\u043f\u0430 \u2116" + str(group_id), reverse('groups'))
    group, group_users, member_ids = await queries.get_group_page_data(request.user, group_id)
    context['group'] = group
    context['users'] = group_users
    context['user'] = request.user

    if group.founder.id is not request.user.id and group_id not in member_ids:
        return await _async_redirect('/groups/')

    if request.POST.get('del') == 'del':
        await queries.delete_group(group)
        return await _async_redirect('/groups/')
    if request.POST.get('del') == 'user':
        await queries.remove_user_from_group(context['user'], context['group'])
        return await _async_redirect('/groups/')

    return await _async_render(request, 'pages/groups/group.html', context)


async def search_friends(request):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u041f\u043e\u0438\u0441\u043a \u0434\u0440\u0443\u0437\u0435\u0439", reverse("search_friends"))
    search_value = request.POST.get('search') if request.method == 'POST' else None
    context['users'], context['users_size'] = await queries.get_search_friends_data(
        request.user,
        search_value,
    )
    context['form'] = SearchFriends(request.POST) if request.method == 'POST' else SearchFriends()

    friend_button = request.POST.get('friend_button')
    if friend_button:
        await queries.create_friend_request(request.user, friend_button)
        return await _async_redirect('/search_friends/')

    return await _async_render(request, 'pages/friends/search_friends.html', context)


async def add_to_group_page(request, group_id: int):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0414\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0432 \u0433\u0440\u0443\u043f\u043f\u0443 \u2116" + str(group_id), reverse('groups'))
    search_value = request.POST.get('search') if request.method == 'POST' else None
    group, users_to_invite, users_size = await queries.get_add_to_group_data(
        request.user,
        group_id,
        search_value,
    )
    context['group'] = group
    context['group_id'] = group_id

    if group.founder.id is not request.user.id:
        return await _async_render(request, 'pages/does_not_found.html', context)
    context['users'] = users_to_invite
    context['users_size'] = users_size
    context['form'] = SearchFriends(request.POST) if request.method == 'POST' else SearchFriends()

    invite = request.POST.get('invite')
    if invite:
        await queries.invite_user_to_group(request.user, context['group'], invite)
        return await _async_redirect('/groups/group/add_to_group/' + str(context['group_id']))

    return await _async_render(request, 'pages/groups/add_to_group.html', context)


async def remove_from_the_group_page(request, group_id: int):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0423\u0434\u0430\u043b\u0435\u043d\u0438\u0435 \u0438\u0437 \u0433\u0440\u0443\u043f\u043f\u044b \u2116" + str(group_id), reverse('groups'))
    search_value = request.POST.get('search') if request.method == 'POST' else None
    group, users_to_remove, users_size = await queries.get_remove_from_group_data(
        request.user,
        group_id,
        search_value,
    )
    context['group'] = group
    context['group_id'] = group_id

    if group.founder.id is not request.user.id:
        return await _async_render(request, 'pages/does_not_found.html', context)
    context['users'] = users_to_remove
    context['users_size'] = users_size
    context['form'] = SearchFriends(request.POST) if request.method == 'POST' else SearchFriends()

    delete_id = request.POST.get('delete')
    if delete_id:
        await queries.remove_member_from_group(delete_id, group_id)
        return await _async_redirect('/groups/group/remove_from_the_group/' + str(context['group_id']))

    return await _async_render(request, 'pages/groups/remove_from_the_group.html', context)


async def report_page(request, report_id: int):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0416\u0430\u043b\u043e\u0431\u0430 \u2116" + str(report_id))
    try:
        report = await queries.get_report_page_data(request.user, report_id)
        if report is None:
            return await _async_render(request, 'pages/does_not_found.html', context)
        context['report'] = report
        context['report_type'] = report.type
        context['id'] = report_id
    except Report.DoesNotExist:
        return await _async_redirect('my_profile/my_reports/')

    return await _async_render(request, 'pages/reports/report.html', context)


async def create_report_page(request):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0421\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u0436\u0430\u043b\u043e\u0431\u044b")
    context['form'] = CreateReportForm(request.POST) if request.method == 'POST' else CreateReportForm()

    if request.method == 'POST':
        if await _async_form_is_valid(context['form']):
            rep = await queries.create_report(request.user, context['form'])
            return await _async_redirect(reverse('report', kwargs={"report_id": rep.id}))

    return await _async_render(request, 'pages/reports/create_report.html', context)


async def my_reports_page(request):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u041c\u043e\u0438 \u0436\u0430\u043b\u043e\u0431\u044b")
    reports, waiting_reports = await queries.get_my_reports_data(request.user)
    context['reports'] = reports
    context['reports_size'] = len(reports)
    context['waiting_reports'] = waiting_reports
    return await _async_render(request, 'pages/reports/my_reports.html', context)


async def unverifed_reports_page(request):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0436\u0430\u043b\u043e\u0431")
    if not request.user.is_superuser:
        return await _async_render(request, 'pages/does_not_found.html', context)

    reports, reports_size = await queries.get_unverified_reports()
    context['reports'] = reports
    context['reports_size'] = reports_size
    return await _async_render(request, 'pages/reports/unverifed_reports.html', context)


async def verify_report_page(request, report_id):
    auth_redirect = await _async_login_required(request)
    if auth_redirect:
        return auth_redirect

    context = get_context(request, "\u0416\u0430\u043b\u043e\u0431\u0430 \u2116" + str(report_id))
    if not request.user.is_superuser:
        return await _async_render(request, 'pages/does_not_found.html', context)

    context['form'] = VerifyReportForm(request.POST) if request.method == 'POST' else VerifyReportForm()
    context['report'] = await queries.get_report_for_verification(report_id)
    context['id'] = report_id

    if context['report'].type == 2:
        return await _async_redirect('/reports/unverifed_reports')

    if request.method == 'POST':
        if await _async_form_is_valid(context['form']):
            await queries.verify_report(
                report_id,
                context['form'].cleaned_data['answer_text'],
            )
            return await _async_redirect('/reports/unverifed_reports')

    return await _async_render(request, 'pages/reports/verify_report.html', context)


