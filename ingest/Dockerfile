# One image, three entrypoints (chosen by the Helm chart's command):
#   python bridge.py        MQTT → Kafka
#   python consumer.py      Kafka → TimescaleDB
#   python dynsec_sync.py   Mosquitto config from appschema.devices (initContainer)
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER 10001

ENV PYTHONUNBUFFERED=1

CMD ["python", "consumer.py"]
