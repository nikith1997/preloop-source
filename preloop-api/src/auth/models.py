from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AuthAPIGenericResponse(BaseModel):
    message: str
    details: Optional[List[Dict[str, Any]]] = None
