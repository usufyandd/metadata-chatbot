from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import api
from api import folders, document_routes
from database import Base, engine


import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base.metadata.create_all(engine)

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range"],
)

#app.include_router(api.router)

@app.get(
    "/",
)
async def home(request: Request):
    return {"message": "Hello Chatbot"}


app.include_router(api.router)
app.include_router(folders.router) 
app.include_router(document_routes.router)
