from fastapi import APIRouter
from dotenv import load_dotenv
from os import getenv

load_dotenv(override=True)

router = APIRouter()


@router.get("/healthz")
def healthz():
    return  {
        "status": "ok",
        "environment": getenv("ENV", "development"),
        "debug": getenv("DEBUG", "false"),
        "version": "1.0.0"
    }
