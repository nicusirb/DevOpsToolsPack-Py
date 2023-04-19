FROM python:3.11.2-alpine3.17

LABEL "maintainer" "Nicusor Sirb"

RUN adduser -h /app -D -u 1000 app

USER app

COPY --chown=app:app ./ /app/

RUN pip install --upgrade pip && \
    pip install -r requirments.txt && \
    mkdir -p /app/shadow/