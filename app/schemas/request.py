from pydantic import BaseModel

class ScanRequest(BaseModel):
    client_id: int
    trace_id: str | None = None
