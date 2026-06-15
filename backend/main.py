from fastapi import FastAPI

from backend import interview_router

app = FastAPI()

app.include_router(interview_router.router)
