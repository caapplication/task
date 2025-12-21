from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer
import uuid
from jose import jwt, JWTError
from typing import List

from . import config

http_bearer = HTTPBearer()

def get_current_user(token: str = Depends(http_bearer)):
    try:
        payload = jwt.decode(token.credentials, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role_scope") or payload.get("role")
        user_id: str = payload.get("user_id") or email
        
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        return {
            "email": email,
            "role": role,
            "id": user_id,
            "agency_id": payload.get("agency_id"),
            "organization_id": payload.get("organization_id")
        }
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def get_current_agency(
    x_agency_id: str = Header(None, alias="x-agency-id"),
    current_user: dict = Depends(get_current_user),
):
    agency_id = x_agency_id or current_user.get("agency_id")
    if not agency_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agency ID is required"
        )
    try:
        return {"id": uuid.UUID(agency_id)}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agency ID format"
        )

def require_role(allowed_roles: List[str]):
    def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", "").upper()
        if user_role not in [role.upper() for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted"
            )
    return role_checker

