import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="YouTube Publisher", version="0.1.0")


class YouTubePublishRequest(BaseModel):
    oauth_access_token: str
    file_url: str
    title: str
    description: str | None = ""
    privacy: str | None = "public"


@app.post("/publish")
def publish(req: YouTubePublishRequest):
    """
    Publish a short video to YouTube via the Data API (resumable upload).
    This endpoint performs a two-step upload: initiate a resumable session, then upload bytes.
    If network access is not available or the file cannot be fetched, an error is returned.
    """
    # Step 1: initiate resumable upload
    snippet = {
        "title": req.title,
        "description": req.description or "",
        "categoryId": "22",  # People & Blogs
    }
    status = {"privacyStatus": req.privacy or "public"}
    init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
    headers = {
        "Authorization": f"Bearer {req.oauth_access_token}",
        "X-Upload-Content-Type": "video/*",
        "Content-Type": "application/json",
    }
    try:
        init_resp = requests.post(init_url, headers=headers, json={"snippet": snippet, "status": status}, timeout=30)
        init_resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube init failed: {e}")
    upload_url = init_resp.headers.get("Location")
    if not upload_url:
        raise HTTPException(status_code=500, detail=f"Upload URL not returned: {init_resp.text}")
    # Step 2: download file from provided file_url
    try:
        file_resp = requests.get(req.file_url, timeout=60)
        file_resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fetching file failed: {e}")
    video_bytes = file_resp.content
    # Step 3: upload to YouTube
    upload_headers = {
        "Authorization": f"Bearer {req.oauth_access_token}",
        "Content-Type": "video/mp4",
    }
    try:
        upload_resp = requests.put(upload_url, headers=upload_headers, data=video_bytes, timeout=300)
        upload_resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube upload failed: {e}")
    try:
        result = upload_resp.json()
    except Exception:
        result = {"raw": upload_resp.text}
    return result
