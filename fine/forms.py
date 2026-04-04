from django import forms

from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm
from fine.models import User, Event


class RegistrationForm(UserCreationForm):
    """
    Форма регистрации пользователя.
    """
    email = forms.EmailField(required=True)

    class Meta:
        """
        fields:
        :param username: Никнейм пользователя
        :param first_name: Имя
        :param last_name: Фамилия
        :param email: Электронная почта
        """
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class CreateEvent(ModelForm):
    """
    Форма создания мероприятия
    """

    class Meta:
        """
        :param name: Название мероприятия
        :param type: Тип (Открытое/Закрытое) мероприятия
        :param address: Адрес проведения мероприятия
        :param start_day: Дата начала мероприятия
        :param finish_day: Дата окончания мероприятия
        :param description: Описание мероприятия
        :param entertainment_type: Тип развлечений мероприятия
        """
        model = Event
        fields = ['name', 'type', 'address', 'start_day', 'finish_day', 'description', 'entertainment_type']


class EditProfile(forms.ModelForm):
    """
    Форма для изменения основных данных профиля пользователя
    """

    class Meta:
        """
        :param username: Никнейм пользователя
        :param first_name: Имя
        :param last_name: Фамилия
        :param email: Электронная почта
        :param avatar: Фото
        """
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'avatar']


class SearchFriends(forms.Form):
    """
    Форма поиска друзей

    :param search: Текст, по которому будет идти поиск :class:`django.forms.CharField`
    """
    search = forms.CharField(max_length=255, label='Введите имя пользователя')

class CreateGroup(forms.Form):
    """
    Форма создания пользовательской группы

    :param title: Название группы :class:`django.forms.CharField`
    :param description: Описание группы :class:`django.forms.CharField`
    """
    title = forms.CharField(max_length=15, label='Название группы', help_text='')
    description = forms.CharField(max_length=255, label='Описание группы', help_text='')

class CreateReportForm(forms.Form):
    """
    Форма для создания репорта
    """
    report_text = forms.CharField(max_length=1024)

class VerifyReportForm(forms.Form):
    """
    Формя для ответа на репорт
    """
    answer_text = forms.CharField(max_length=1024, label="Напишите ответ на жалобу пользователя")
