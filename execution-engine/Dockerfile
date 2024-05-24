FROM python:3.11

RUN apt-get update && apt-get install -y curl software-properties-common && apt-get install -y jq
RUN pip install poetry

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

WORKDIR /preloop-execution-engine
COPY pyproject.toml ./
COPY send_execution_status.py ./
COPY pysnooper_file.py ./

ARG DEPLOY_ENVIRONMENT
ARG AWS_DEFAULT_REGION
ARG AWS_ACCOUNT_ID

ENV DEPLOY_ENVIRONMENT=${DEPLOY_ENVIRONMENT}
ENV AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
ENV AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}

RUN poetry config virtualenvs.create false && \
poetry install --no-root

COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

RUN mkdir -p /preloop-execution-engine/execution_script
ENTRYPOINT ["./entrypoint.sh"]