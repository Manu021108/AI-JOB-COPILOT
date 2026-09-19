from typing import Any
from fastapi import HTTPException, status


class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def ok(data: Any = None) -> dict:
    return {"success": True, "data": data}


def error_response(error: ApiError) -> dict:
    return {"success": False, "error": {"code": error.code, "message": error.message}}


def raise_api(error: ApiError) -> None:
    raise HTTPException(status_code=error.status_code, detail=error_response(error))