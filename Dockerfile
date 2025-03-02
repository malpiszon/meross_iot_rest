ARG PYTHON_IMAGE_VERSION=3.13-alpine
FROM python:${PYTHON_IMAGE_VERSION} AS builder

RUN apk add --no-cache gcc musl-dev libffi-dev

RUN python3 -m venv /venv
ENV PATH=/venv/bin:$PATH

WORKDIR /build
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt


ARG PYTHON_IMAGE_VERSION=3.13-alpine
FROM python:${PYTHON_IMAGE_VERSION} AS app

ARG PYTHON_IMAGE_VERSION
LABEL org.opencontainers.image.base.name="python:${PYTHON_IMAGE_VERSION}"
LABEL org.opencontainers.image.licenses=MIT
LABEL org.opencontainers.image.source=https://github.com/malpiszon/meross_iot_rest
LABEL org.opencontainers.image.title=meross_iot_rest

COPY --from=builder /venv /venv
ENV PATH=/venv/bin:$PATH

RUN adduser -D worker
USER worker

WORKDIR /app
COPY --chown=worker:worker meross_iot_rest.py .

CMD ["python3", "meross_iot_rest.py"]
