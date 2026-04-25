Project Overview
================

Purpose
-------

FinE is a server-rendered web application that helps users discover events and coordinate attendance with other people. The project is aimed at social scenarios where a user wants to find an activity, join it, invite friends, or manage participation through a personal group.

Core capabilities
-----------------

- user registration and authentication with a custom Django user model
- public and private events
- personal event feed with recommendation ranking
- user profiles and avatars
- friend requests and confirmed friendships
- user-created groups
- report submission by users and moderation by administrators
- theme switching for authenticated users

Roles
-----

Anonymous user
--------------

- can view the home page
- can browse public parts of the application
- can register and log in

Authenticated user
------------------

- can create and edit events
- can join events
- can view a recommendation feed
- can manage friends, groups, reports, and profile data

Administrator
-------------

- can access Django admin
- can review unresolved reports

Application style
-----------------

The project is a classic Django monolith:

- routing is declared in ``fine_project/urls.py``
- business logic is mostly located in ``fine/views.py``
- HTML is rendered through Django templates in ``fine/templates/``
- styling and frontend scripts are in ``fine/static/``

Main sections
-------------

- ``/``: landing page
- ``/menu/``: event catalog with filtering by entertainment type
- ``/feed/``: personalized recommendations for a logged-in user
- ``/menu/event/create/``: event creation
- ``/friends/`` and ``/search_friends/``: friendship workflows
- ``/groups/``: user groups
- ``/reports/...``: report creation, viewing, and moderation
