FROM python:3.12.0-slim-bullseye

# set working directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apt-get update \
  && apt-get -y install netcat gcc postgresql curl \
  && apt-get clean

RUN curl -sSL https://install.python-poetry.org | python3 -

# install python dependencies
RUN $HOME/.local/bin/poetry config virtualenvs.create false
COPY poetry.lock pyproject.toml ./
RUN $HOME/.local/bin/poetry install
