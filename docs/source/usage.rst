User Scenarios
==============

Authentication
--------------

- registration page: ``/registration/``
- login page: ``/login/``
- logout page: ``/logout/``

After login, the navigation menu expands and gives access to recommendations, friends, groups, profile, and reports.

Events
------

Public catalog
--------------

- the event catalog is available at ``/menu/``
- the page shows active public events
- users can filter events by entertainment type

Event creation
--------------

- authenticated users can create an event at ``/menu/event/create/``
- after creation, the author is redirected to a participation flow for the new event
- event dates are validated so the finish date cannot be earlier than the start date

Event participation
-------------------

- event detail page: ``/menu/event/<event_id>``
- a user can join an event
- private events are hidden from users who are not participants
- the page also shows which friends are already attending the event

Recommendations
---------------

- recommendation feed: ``/feed/``
- available only to authenticated users
- if the user has no stored recommendations, the feed triggers recommendation generation automatically
- recommendations can be filtered by entertainment type

The ranking logic currently considers:

- event entertainment type against user interests when such relation exists
- current member count
- how soon the event starts

Friends
-------

- friends page: ``/friends/``
- friend search page: ``/search_friends/``

Supported actions:

- send a friend request
- cancel a sent request
- accept an incoming request
- remove an existing friend

Groups
------

- group list: ``/groups/?action=watch``
- group creation: ``/groups/create_group/``
- group detail: ``/groups/group/<group_id>/``

Groups are used as a convenient container of users. A group founder can:

- add friends to the group
- remove users from the group
- invite the whole group to an event

Reports
-------

For regular users:

- create a report at ``/reports/my_reports/create/report``
- view own reports at ``/reports/my_reports/``
- open a report detail page

For administrators:

- view unresolved reports at ``/reports/unverifed_reports``
- answer a report at ``/reports/verify/report/<report_id>``

Profile and theme
-----------------

- profile page: ``/profile/<user_id>``
- profile edit page: ``/profile/edit/about``
- theme toggle endpoint: ``/theme/change/``

Authenticated users can edit their profile data and avatar. Theme switching stores the selected mode in the ``User.theme`` field.
