import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="TikTok Publisher", version="0.1.0")


class TikTokPublishRequest(BaseModel):
    user_access_token: str
    video_url: str
    title: str
    privacy_level: str | None = "PUBLIC_TO_EVERYONE"
    disable_duet: bool = False
    disable_stitch: bool = False
    disable_comment: bool = False


@app.post("/publish")
def publish(req: TikTokPublishRequest):
    """
    Publish a video to TikTok using the Content Posting API Direct Post endpoint.
    Note: Unless your app has passed TikTok's audit, posts may default to private visibility.
    """
    body = {
        "post_info": {
            "title": req.title,
            "privacy_level": req.privacy_level,
            "disable_duet": req.disable_duet,
            "disable_stitch": req.disable_stitch,
            "disable_comment": req.disable_comment,
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "video_url": req.video_url,
        },
    }
    headers = {
        "Authorization": f"Bearer {req.user_access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    try:
        resp = requests.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            headers=headers,
            json=body,
            timeout=30,
        )
        # TikTok returns JSON even on some errors; don't raise for status to capture body
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TikTok publish failed: {e}")
    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=500, detail=f"TikTok response not JSON: {resp.text}")
    # Forward the entire response to the caller for transparency
    return {"status_code": resp.status_code, "response": data}
