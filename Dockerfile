FROM python:3.12.3-alpine

RUN apk add --no-cache curl

RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY . .

ARG SERVER_ADDRESS
ARG POSTGRES_CONN

ENV SERVER_ADDRESS=${SERVER_ADDRESS}
ENV POSTGRES_CONN=${POSTGRES_CONN}

RUN poetry install --no-interaction

ENTRYPOINT ["poetry", "run", "python3", "core/main.py"]

EXPOSE 8080