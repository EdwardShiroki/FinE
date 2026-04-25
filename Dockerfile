FROM python:3.10
LABEL authors="urtanto"

RUN mkdir proj
WORKDIR /proj

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV debug=False

COPY requirements.txt /proj/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /proj/
RUN chmod +x /proj/start.sh

ENTRYPOINT ["./start.sh"]
