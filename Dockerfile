FROM python:3.10
LABEL authors="urtanto"

RUN mkdir -p /proj /var/static /proj/media
WORKDIR /proj

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV debug=False

COPY requirements.txt /proj/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /proj/
RUN python3 manage.py collectstatic --noinput

CMD ["gunicorn", "fine_project.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "120", "--workers", "3"]
