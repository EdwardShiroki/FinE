import json
from datetime import datetime

from django.core.handlers.wsgi import WSGIRequest
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from django.template.defaultfilters import register
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib import messages

from fine.models import User, Event, Friends, UserGroups, Report
from fine.forms import EditProfile, RegistrationForm, CreateEvent, SearchFriends, CreateGroup, \
    VerifyReportForm, CreateReportForm


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


def get_context(request: WSGIRequest = None, page_name="", active="") -> dict:
    """
    Функция для возвращения контекста меню

    :return: контекст меню
    """
    data = {
        'pagename': page_name,
        "active": active,
        "menu": {
            "left": {
                "unauthorized": [
                    {'url_name': '/', 'name': 'Главная страница'},
                    {'url_name': '/menu/', 'name': 'Меню'},
                ],
            },
            "right": {
                "unauthorized": [
                    {'url_name': '/registration/', 'name': 'Зарегистрироваться'},
                    {'url_name': '/login/', 'name': 'Войти', "button-style": "btn-outline-primary"},
                ],
            },
        }
    }
    if not request:
        return data
    if request.user.is_authenticated:
        data["menu"]["left"]["authorized"] = [
            {'url_name': reverse('index'), 'name': 'Главная страница'},
            {'url_name': reverse('menu'), 'name': 'Меню'},
            {'url_name': reverse('friends'), 'name': 'Друзья'},
            {'url_name': reverse('search_friends'), 'name': 'Найти друга'},
        ]
        data["menu"]["right"]["authorized"] = [
            {'url_name': reverse('unverifed_reports') if request.user.is_superuser
            else reverse('my_reports'), 'name': 'Жалобы'},
            {'url_name': '/groups?action=watch', 'name': 'Группы'},
            {'url_name': reverse('profile', kwargs={'code': request.user.id}), 'name': 'Профиль'},
            {'url_name': reverse('logout'), 'name': 'Выйти', "button-style": "btn-outline-primary"},
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
    context = get_context(request, "Wellcome", reverse("index"))
    context["events"] = list(Event.objects.filter(type=1))[: 3]
    return render(request, 'pages/start/index.html', context)


def error_page(request: WSGIRequest):
    """
    Страница ошибки
    """
    context = get_context(request, "Error")
    return render(request, 'pages/does_not_found.html', context)


@defense
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
        context['errors'] = form.errors
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
