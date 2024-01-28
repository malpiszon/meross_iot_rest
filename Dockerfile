FROM python:3.12-alpine AS builder

RUN apk add --no-cache gcc musl-dev libffi-dev

RUN python3 -m venv /venv
ENV PATH=/venv/bin:$PATH

WORKDIR /build
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt


FROM python:3.12-alpine AS app

COPY --from=builder /venv /venv
ENV PATH=/venv/bin:$PATH
RUN pip install setuptools

RUN adduser -D worker
USER worker

WORKDIR /app
COPY --chown=worker:worker meross_iot_rest.py .

CMD ["waitress-serve", "--host", "0.0.0.0", "meross_iot_rest:app"]
