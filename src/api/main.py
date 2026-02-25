from fastapi import FastAPI
from src.api.routes import devices, incidents, lifecycle

app = FastAPI(
    title="Enterprise Asset Lifecycle API",
    description="Synthetic ITAM / CMDB REST API",
    version="1.0.0"
)

app.include_router(devices.router)
app.include_router(incidents.router)
app.include_router(lifecycle.router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}