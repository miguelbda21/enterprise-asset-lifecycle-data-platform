from fastapi import FastAPI
from src.api.routes import devices, incidents, lifecycle
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

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