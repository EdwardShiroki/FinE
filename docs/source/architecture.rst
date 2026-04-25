Architecture
============

Project layout
--------------

``fine/``
   main application with models, views, forms, templates, static assets, tests, and management commands

``fine_project/``
   Django project configuration: settings, URL map, ASGI and WSGI entry points

``docs/``
   Sphinx source and generated documentation

Request flow
------------

1. URLs are declared in ``fine_project/urls.py``.
2. Most requests are handled by function-based views in ``fine/views.py``.
3. Views load or modify data through Django ORM models in ``fine/models.py``.
4. Responses are rendered through templates under ``fine/templates/``.
5. Static CSS and JavaScript are served from ``fine/static/``.

Data model
----------

``User``
   custom authentication model derived from ``AbstractUser`` with additional fields ``status``, ``avatar``, and ``theme``

``UserSettings``
   one-to-one extension point for per-user settings

``Event``
   event entity with owner, type, dates, description, entertainment type, and participants

``Report``
   user report with moderation status and answer text

``Friends``
   directed relation representing friend requests and confirmed friendships

``UserGroups``
   named user collections created by a founder

``UserRecommendation``
   cached recommendation results for a user with score, rank, and generation timestamp

Recommendation subsystem
------------------------

The recommendation logic lives in ``fine/services/recommendations.py``.

Generation steps:

1. select active events
2. exclude events authored by the target user
3. exclude events the user already joined
4. calculate a score for each remaining event
5. sort events by score
6. store the top results in ``UserRecommendation``

There is also a management command:

.. code-block:: bash

   python manage.py rebuild_recommendations

Templates and frontend
----------------------

- templates are grouped by feature area: ``start``, ``main``, ``event``, ``friends``, ``groups``, ``profile``, ``reports``
- JavaScript files provide theme switching, event interactions, tabs, and map-related helpers
- the project uses Bootstrap 5, but the UI remains primarily server-rendered

Operational notes
-----------------

- The project is not an API-first application; the main integration surface is HTML pages.
- Business logic is concentrated in a single views module, which simplifies entry but increases coupling.
- Some historical traces remain in the repository, such as references to ``user.interests`` in recommendation scoring and an unused template for editing interests. These references are useful to know during maintenance because they suggest partially removed or unfinished functionality.
