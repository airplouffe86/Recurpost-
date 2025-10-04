import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="IG Publisher", version="0.1.0")


class IGPublishRequest(BaseModel):
    ig_user_id: str
    video_url: str
    caption: str
    access_token: str


@app.post("/publish")
def publish(req: IGPublishRequest):
    """
    Publish a reel to Instagram via the Graph API.
    The client must supply a valid ig_user_id and access_token for a professional account.
    """
    # Create media container
    container_params = {
        "media_type": "REELS",
        "video_url": req.video_url,
        "caption": req.caption,
        "access_token": req.access_token,
    }
    container_url = f"https://graph.facebook.com/v20.0/{req.ig_user_id}/media"
    try:
        resp = requests.post(container_url, data=container_params, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IG media container creation failed: {e}")
    container_data = resp.json()
    creation_id = container_data.get("id") or container_data.get("creation_id")
    if not creation_id:
        raise HTTPException(status_code=500, detail=f"IG media container missing creation_id: {container_data}")
    # Publish the media
    publish_url = f"https://graph.facebook.com/v20.0/{req.ig_user_id}/media_publish"
    try:
        publish_resp = requests.post(
            publish_url,
            data={"creation_id": creation_id, "access_token": req.access_token},
            timeout=30,
        )
        publish_resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IG media publish failed: {e}")
    return publish_resp.json()
