# main.py stable work. push
import sys
import asyncio

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, Depends, Header, status
from typing import List
from pydantic import BaseModel
from placesCrawlerV2 import search
from starlette.concurrency import run_in_threadpool
import os

app = FastAPI()

class SearchRequest(BaseModel):
    business_type: str
    location: str

class SearchResult(BaseModel):
    company_name: str
    address: str
    website: str
    company_phone: str

async def verify_api_key(x_api_key: str = Header(...)):
    api_key_env = os.environ.get('API_KEY')
    if api_key_env is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API Key not configured on the server."
        )
    if x_api_key != api_key_env:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )

@app.post("/search", response_model=List[SearchResult], dependencies=[Depends(verify_api_key)])
async def read_search(request: SearchRequest):
    results = await run_in_threadpool(search, request.business_type, request.location)
    return results
