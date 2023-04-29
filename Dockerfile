FROM python:3.11.2

LABEL "maintainer" "Nicu Sirb"

RUN apt-get update && \
    apt-get install -y vim python3-waitress && \
    adduser --home /app --uid 1000 --disabled-password --gecos 'app' app

USER app
WORKDIR /app

COPY --chown=app:app ./ /app/

RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt && \
    mkdir -p /app/shadow/

ENTRYPOINT [ "python3" ]
CMD [ "main.py" ]