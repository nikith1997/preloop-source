FROM python:3.11
RUN apt-get update && apt-get upgrade -y && apt-get install -y curl software-properties-common && apt-get install -y jq
RUN pip install poetry

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

ARG DEPLOY_ENVIRONMENT
ARG AWS_DEFAULT_REGION
ARG AWS_ACCOUNT_ID

ENV DEPLOY_ENVIRONMENT=${DEPLOY_ENVIRONMENT}
ENV AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
ENV AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY src/ /app/src/

RUN poetry config virtualenvs.create false && \
poetry install --no-root

COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

RUN cd src && export PYTHONPATH=$PWD && cd ..
ENTRYPOINT ["./entrypoint.sh"]
