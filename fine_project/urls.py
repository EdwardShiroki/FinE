"""djangoProject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, re_path

from fine_project import settings
from fine import views

urlpatterns = [
    path('', views.index_page, name='index'),
    path('error/', views.error_page, name="error"),
    path('profile/<int:code>', views.profile_view_page, name='profile'),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_page, name='logout'),
    path('menu/', views.menu_page, name='menu'),
    path('feed/', views.feed_page, name='feed'),
    path('menu/event/create/', views.event_create_page, name='event_create'),
    path('menu/event/edit/<int:event_id>', views.event_edit_page, name='event_edit'),
    path('menu/event/commit/<int:event_id>', views.commit_event_page, name='event_commit'),
    path('menu/event/commit/group/<int:event_id>/<int:group_id>',
         views.commit_event_group_page, name='event_group_commit'),
    path('registration/', views.registration_page, name='register'),
    path('profile/edit/about', views.edit_page, name='edition_about'),
    path('menu/event/<int:event_id>', views.event_page, name='event'),
    path('friends/', views.friends_page, name='friends'),
    path('search_friends/', views.search_friends, name='search_friends'),
    path('groups/create_group/', views.create_group_page, name='create_group'),
    path('groups/', views.groups_page, name='groups'),
    path('groups/group/<int:group_id>/', views.group_page, name='group'),
    path('groups/group/add_to_group/<int:group_id>', views.add_to_group_page, name='add_to_group'),
    path('groups/group/remove_from_the_group/<int:group_id>',
         views.remove_from_the_group_page, name='remove_from_the_group'),
    path('theme/change/', views.theme_change),
    path('reports/my_reports/', views.my_reports_page, name='my_reports'),
    path('reports/my_reports/create/report', views.create_report_page, name='create_report'),
    path('reports/my_reports/report/<int:report_id>', views.report_page, name='report'),
    path('reports/verify/report/<int:report_id>', views.verify_report_page, name='verify_report'),
    path('reports/unverifed_reports', views.unverifed_reports_page, name='unverifed_reports'),
]

urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", views.media_file),
    re_path(r"^fine/static/(?P<path>.*)$", views.static_file),
]
