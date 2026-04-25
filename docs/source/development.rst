Development Notes
=================

Custom user model
-----------------

The project defines ``AUTH_USER_MODEL = 'fine.User'``. When adding new relations or querying the active user model, use:

.. code-block:: python

   from django.contrib.auth import get_user_model

This avoids hard-coding Django's default ``auth.User``.

Tests
-----

The repository currently contains a small but useful test baseline:

- ``fine/tests/test_auth.py`` verifies that the root page responds successfully
- ``fine/tests/test_recommendations.py`` verifies lazy generation of recommendations in the feed

Run tests with:

.. code-block:: bash

   python manage.py test

Management commands
-------------------

Available custom command:

- ``rebuild_recommendations``: rebuilds recommendation cache for all users

Example:

.. code-block:: bash

   python manage.py rebuild_recommendations --limit 50 --batch-size 200

Configuration details
---------------------

- ``DEBUG`` is derived from the environment variable ``debug``
- when ``debug=False``, database settings switch to PostgreSQL
- Kubernetes bootstrap job runs ``python manage.py migrate --noinput`` before backend rollout
- the backend image starts ASGI directly via ``gunicorn`` + ``uvicorn.workers.UvicornWorker``
- Redis cache and PostgreSQL endpoints are injected through environment variables

Known technical constraints
---------------------------

- ``fine/views.py`` contains most application logic, so feature changes often touch the same file
- authorization checks are implemented directly in views rather than through separate service layers
- recommendation scoring references a potential ``user.interests`` relation that is not present in the current ``fine/models.py``
- route naming and page naming are not fully uniform, so documentation should be preferred over guessing URLs from conventions

Suggested next improvements
---------------------------

- split large views into feature modules
- expand test coverage around groups, reports, and event participation
- move secrets and database credentials fully to environment variables
- document deployment separately from local development
