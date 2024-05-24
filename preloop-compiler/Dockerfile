FROM python:3.11

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

RUN apt-get update && apt-get install -y apt-transport-https && apt-get -y upgrade \
    && apt-get install -y \
    build-essential \
    curl \
    lsb-release \
    locales \
    gnupg

RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

ARG APP_PATH=/app
WORKDIR ${APP_PATH}/

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock poetry.toml ${APP_PATH}/

# Install only dependencies
RUN poetry install --no-root --no-interaction --no-ansi

COPY . ${APP_PATH}

# Should not run as root, so change to python
RUN chown -R python:python ${APP_PATH}

USER python

# Add venv to PATH
ENV PATH="${APP_PATH}/.venv/bin:$PATH"

# TODO: update to use the port for your service
EXPOSE 8080

# Start
ENV APP_START=${APP_PATH}/docker-entrypoint.py
CMD ${APP_START}
