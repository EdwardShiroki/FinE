from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.db import models


class EntertainmentType(models.IntegerChoices):
    """
    Типы интересов
    """
    SPORT = 0
    MEETING = 1
    GAME = 2
    ENTERTAINMENT = 3


class User(AbstractUser):
    """
    Класс пользователя

    :param avatar: Фото пользователя :class:`django.db.models.ImageField`
    :param theme: Тема сайта
    """
    status = models.CharField(max_length=255)
    avatar = models.ImageField(upload_to='images/', blank=True, null=True)
    theme = models.CharField(max_length=255, default="white")


class UserSettings(models.Model):
    """
    Настройки пользователя
    """
    user = models.OneToOneField(to=get_user_model(), on_delete=models.CASCADE)


class Event(models.Model):
    """
    База мероприятий

    :param name: Название мероприятия :class:`django.db.models.CharField`
    :param type: Тип мероприятия :class:`django.db.models.IntegerField`
    :param address: Адрес мероприятия :class:`django.db.models.CharField`
    :param status: Статус мероприятия :class:`django.db.models.BooleanField`
    :param start_day: Дата начала мероприятия :class:`django.db.models.DateField`
    :param finish_day: Дата конца мероприятия :class:`django.db.models.DateField`
    :param description: Описание мероприятия :class:`django.db.models.CharField`
    :param author: Создатель мероприятия :class:`django.db.models.ForeignKey`
    :param members: Участники мероприятия :class:`django.db.models.ManyToManyField`
    """
    name = models.CharField(max_length=255)

    class Type(models.IntegerChoices):
        """
        Тип мероприятия

        :param close: Закрытое мероприятие
        :param open: Открытое мероприятие
        """
        CLOSE = 0
        OPEN = 1

    type = models.IntegerField(choices=Type.choices)
    address = models.CharField(max_length=255)
    status = models.BooleanField(default=True)  # False - Close, True - Active
    start_day = models.DateField()
    finish_day = models.DateField()
    description = models.TextField()
    author = models.ForeignKey(get_user_model(), models.CASCADE, related_name='author')
    entertainment_type = models.IntegerField(choices=EntertainmentType.choices, default=1)
    members = models.ManyToManyField(get_user_model(), related_name='event_members')

class Report(models.Model):
    """
    База жалоб/вопросов пользователей

    :param author: Автор жалобы :class:`django.db.models.ForeignKey`
    :param report_text: Текст вопроса жалобы :class:`django.db.models.TextField`
    :param answer_text: Текст ответа на жалобу :class:`django.db.models.TextField`
    :param created_at: Дата создания :class:`django.db.models.DateTimeField`
    :param closed_at: Дата закрытия :class:`django.db.models.DateTimeField`
    :param type: Тип жалобы :class:`django.db.models.IntegerField`
    """

    class Type(models.IntegerChoices):
        """
        Тип жалобы

        :param waiting: Жалоба в обработке
        :param close: Жалоба проверена
        """
        WAITING = 1
        CLOSE = 2

    author = models.ForeignKey(get_user_model(), models.CASCADE)
    report_text = models.TextField()
    answer_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    closed_at = models.DateTimeField(blank=True, null=True)
    type = models.IntegerField(choices=Type.choices)


class Friends(models.Model):
    """
    База друзей

    :param from_user: От какого пользователя :class:`django.db.models.ForeignKey`
    :param to_user: К какому пользователю :class:`django.db.models.ForeignKey`
    :param waiting: Существует ли запрос, или пользователи уже друзья :class:`django.db.models.BooleanField`
    """
    from_user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='who_send')
    to_user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='who_receive')
    waiting = models.BooleanField()


class UserGroups(models.Model):
    """
    База пользовательских групп

    :param title: Название группы :class:`django.db.models.CharField`
    :param description: Описание группы :class:`django.db.models.CharField`
    :param founder: Создатель группы :class:`django.db.models.ForeignKey`
    :param members: Пользователи группы :class:`django.db.models.ManyToManyField`

    """
    title = models.CharField(max_length=15)
    description = models.CharField(max_length=255)
    founder = models.ForeignKey(get_user_model(), models.CASCADE, related_name='founder')
    members = models.ManyToManyField(get_user_model(), related_name='members')
