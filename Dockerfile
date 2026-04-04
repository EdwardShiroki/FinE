FROM python:3.10
LABEL authors="urtanto"

RUN mkdir proj
WORKDIR /proj

ENV PYTHONUNBUFFERED 1
ENV debug "False"

COPY requirements.txt /proj/
RUN pip install -r requirements.txt
COPY . /proj/

ENTRYPOINT ./start.sh