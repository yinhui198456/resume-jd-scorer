from fastapi import APIRouter

from api import answers, evaluate, history, jds, parse, resumes

api_router = APIRouter(prefix="/api")
api_router.include_router(jds.router)
api_router.include_router(resumes.router)
api_router.include_router(evaluate.router)
api_router.include_router(parse.router)
api_router.include_router(answers.router)
api_router.include_router(history.router)
