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

class SearchResult(BaseModel):
    company_name: str
    address: str
    website: str
    company_phone: str

@app.get("/search", response_model=List[SearchResult])
async def read_search(location: str, business_type: str):
    results = await run_in_threadpool(search, location, business_type)
    return results
