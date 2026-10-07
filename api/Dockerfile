FROM python:3.12-slim

# Signal to the application that it is running inside a container.
# This prevents the app from trying to load a .env file (which is not
# present in the image — see .dockerignore). Secrets are injected via
# K8s secretKeyRef environment variables at runtime.
ENV IN_CONTAINER=true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user (the app and migrations only need read access)
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER 10001

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
