Setup and Run
=============

Requirements
------------

- Python 3.10 or newer
- pip
- virtual environment support
- optional: Docker and Docker Compose for containerized start

Local development
-----------------

1. Create a virtual environment and activate it.
2. Install dependencies:

.. code-block:: bash

   pip install -r requirements.txt

3. Apply database migrations:

.. code-block:: bash

   python manage.py migrate

4. Optional: create a superuser:

.. code-block:: bash

   python manage.py createsuperuser

5. Start the development server:

.. code-block:: bash

   python manage.py runserver

6. Open the application:

   ``http://127.0.0.1:8000/``

Database behavior
-----------------

- With the current settings, development mode uses SQLite at the project root.
- If the environment variable ``debug=False`` is provided, Django switches to PostgreSQL.
- The Docker stack is configured for PostgreSQL and expects the service name ``db``.

Docker run
----------

Build and start the application with Docker Compose:

.. code-block:: bash

   docker compose up --build

By default:

- PostgreSQL runs in the ``db`` service
- the Django container runs in the ``back`` service
- the application is exposed on port ``8001``

Static and media files
----------------------

- local development serves media when ``DEBUG=True``
- media is stored in ``media/``
- static source files are stored in ``fine/static/``
- in containerized mode, the startup script runs ``collectstatic`` before ``gunicorn``

Documentation build
-------------------

Build the HTML documentation:

.. code-block:: bash

   make -C docs html

Open the generated documentation entry point:

.. code-block:: bash

   open docs/build/html/index.html

If your system does not support ``open``, open this file path manually in a browser:

``docs/build/html/index.html``
