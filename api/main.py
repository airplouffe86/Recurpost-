import os
import json
import uuid
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


DATA_PATH = os.environ.get("DATA_PATH", "/app/data")
os.makedirs(DATA_PATH, exist_ok=True)

def _load(filename: str) -> List[Dict]:
    path = os.path.join(DATA_PATH, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(filename: str, data: List[Dict]):
    path = os.path.join(DATA_PATH, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

app = FastAPI(title="RecurPost++ API", version="0.1.0")

# Models

class LibraryCreate(BaseModel):
    name: str

class LibraryItemCreate(BaseModel):
    master_url: str
    title: Optional[str] = None

class CaptionCreate(BaseModel):
    library_item_id: str
    platform: str
    body: str

class AccountCreate(BaseModel):
    network: str
    external_user_id: str
    handle: str
    access_token: Optional[str] = None

class ScheduleCreate(BaseModel):
    account_id: str
    post_times: List[str]

# Helpers for state

def _generate_id() -> str:
    return uuid.uuid4().hex

# Load data structures from disk on startup
libraries = _load("libraries.json")
library_items = _load("library_items.json")
captions = _load("captions.json")
accounts = _load("accounts.json")
schedules = _load("schedules.json")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/libraries")
def create_library(lib: LibraryCreate):
    new_id = _generate_id()
    libraries.append({"id": new_id, "name": lib.name})
    _save("libraries.json", libraries)
    return {"id": new_id, "name": lib.name}


@app.get("/libraries")
def list_libraries():
    return libraries


@app.post("/libraries/{library_id}/items")
def create_library_item(library_id: str, item: LibraryItemCreate):
    # Check library existence
    if not any(l["id"] == library_id for l in libraries):
        raise HTTPException(status_code=404, detail="Library not found")
    new_id = _generate_id()
    library_items.append({"id": new_id, "library_id": library_id, "master_url": item.master_url, "title": item.title})
    _save("library_items.json", library_items)
    return {"id": new_id, "library_id": library_id, "master_url": item.master_url, "title": item.title}


@app.get("/libraries/{library_id}/items")
def list_library_items(library_id: str):
    return [item for item in library_items if item["library_id"] == library_id]


@app.post("/captions")
def create_caption(caption: CaptionCreate):
    # Basic validation: library_item exists
    if not any(item["id"] == caption.library_item_id for item in library_items):
        raise HTTPException(status_code=404, detail="Library item not found")
    new_id = _generate_id()
    captions.append({"id": new_id, "library_item_id": caption.library_item_id, "platform": caption.platform, "body": caption.body})
    _save("captions.json", captions)
    return {"id": new_id, "library_item_id": caption.library_item_id, "platform": caption.platform, "body": caption.body}


@app.get("/captions/{library_item_id}")
def list_captions(library_item_id: str):
    return [c for c in captions if c["library_item_id"] == library_item_id]


@app.post("/accounts")
def create_account(acc: AccountCreate):
    new_id = _generate_id()
    accounts.append({"id": new_id, "network": acc.network, "external_user_id": acc.external_user_id, "handle": acc.handle, "access_token": acc.access_token})
    _save("accounts.json", accounts)
    return {"id": new_id, "network": acc.network, "external_user_id": acc.external_user_id, "handle": acc.handle}


@app.get("/accounts")
def list_accounts():
    return accounts


@app.post("/schedules")
def create_schedule(sched: ScheduleCreate):
    # Validate account existence
    if not any(a["id"] == sched.account_id for a in accounts):
        raise HTTPException(status_code=404, detail="Account not found")
    new_id = _generate_id()
    schedules.append({"id": new_id, "account_id": sched.account_id, "post_times": sched.post_times})
    _save("schedules.json", schedules)
    return {"id": new_id, "account_id": sched.account_id, "post_times": sched.post_times}


@app.get("/schedules/{account_id}")
def list_schedules(account_id: str):
    return [s for s in schedules if s["account_id"] == account_id]
