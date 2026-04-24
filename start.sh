python3 manage.py migrate
python3 manage.py collectstatic
gunicorn fine_project.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 120 --workers 3
