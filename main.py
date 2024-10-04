# main.py
import sys
import asyncio

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from typing import List
from pydantic import BaseModel
from placesCrawlerV2 import search
from starlette.concurrency import run_in_threadpool

app = FastAPI()

class SearchRequest(BaseModel):
    business_type: str
    location: str

class SearchResult(BaseModel):
    company_name: str
    address: str
    website: str
    company_phone: str

@app.post("/search", response_model=List[SearchResult])
async def read_search(request: SearchRequest):
    results = await run_in_threadpool(search, request.business_type, request.location)
    return results
