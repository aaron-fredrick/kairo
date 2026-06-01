from pydantic import BaseModel
from typing import Optional, Dict, Any

class HealthCheckResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, str]

class LogSchema(BaseModel):
    level: str
    message: str
    service_name: str
    timestamp: str
    context: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
