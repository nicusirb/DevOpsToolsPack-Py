FROM python:3.11.2-alpine3.17

RUN pip install --upgrade pip && \
    python3 -m pip install boto3

USER 1000
RUN mkdir -p ~/pem_keys/