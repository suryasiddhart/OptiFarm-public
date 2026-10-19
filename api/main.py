"""
FarmApp API — FastAPI application entry point.

Uses SQLAlchemy in text mode (raw SQL) for database operations.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from config.settings import settings
from routes import auth, devices, fields, moisture
from routes import users


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        routes=app.routes,
        # Behind the ingress the API lives under /api: "Try it out" must call /api/...
        servers=[{"url": settings.root_path}] if settings.root_path else None,
    )
    # Register BOTH scheme names so Swagger UI recognises them all
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    # None disables the route; without openapi_url there is no schema at all
    docs_url="/docs" if settings.api_docs_enabled else None,
    redoc_url="/redoc" if settings.api_docs_enabled else None,
    openapi_url="/openapi.json" if settings.api_docs_enabled else None,
    # Path prefix the ingress strips before forwarding (ROOT_PATH=/api in the
    # backend chart); Swagger UI then loads /api/openapi.json.
    root_path=settings.root_path,
)

app.openapi = custom_openapi

# CORS: only for explicitly listed origins. The frontend is served from the
# same host as the API (/api), so normal use needs no CORS. Credentials stay
# off: auth is a bearer token in the Authorization header, not a cookie.
if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(fields.router)
app.include_router(moisture.router)
app.include_router(devices.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

