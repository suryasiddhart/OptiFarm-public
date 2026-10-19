FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER 10001

ENV PYTHONUNBUFFERED=1 \
    SIMULATOR_DEVICES_FILE=/config/devices.yaml

CMD ["python", "main.py"]
