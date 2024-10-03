# main.py
import sys
import asyncio

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from typing import List, Optional
from pydantic import BaseModel
from placesCrawlerV2 import search
from starlette.concurrency import run_in_threadpool

app = FastAPI()

class SearchResult(BaseModel):
    id: str
    title: str
    category: str
    address: str
    phoneNumber: str
    completePhoneNumber: str
    domain: str
    url: str
    coor: str
    stars: Optional[float]  # Use float
    reviews: Optional[int]  # Use int

@app.get("/search", response_model=List[SearchResult])
async def read_search(query: str):
    results = await run_in_threadpool(search, query)
    return results
