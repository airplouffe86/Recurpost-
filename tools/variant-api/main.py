import os
import uuid
import subprocess
import shutil
from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    import boto3  # type: ignore
except ImportError:
    boto3 = None  # S3 uploads will be disabled if boto3 is unavailable


app = FastAPI(title="Variant API", version="0.1.0")

# Environment variables controlling S3 and CDN configuration
S3_BUCKET = os.environ.get("S3_BUCKET")
CDN_URL = os.environ.get("CDN_URL")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

if boto3 and S3_BUCKET:
    s3_client = boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )
else:
    s3_client = None

# Ensure static directory exists for fallback file serving
STATIC_DIR = os.path.join(os.getcwd(), "static")
os.makedirs(STATIC_DIR, exist_ok=True)


class VariantRequest(BaseModel):
    file_url: str  # URL to the master video file
    platform: str = "generic"
    seed: str | None = None


def run_ffmpeg(input_url: str, output_path: str, seed: str | None) -> None:
    """Run FFmpeg to create a perceptual fresh variant."""
    vf = "scale=iw*1.01:ih*1.01,crop=iw:ih,pad=ceil(iw/2)*2:ceil(ih/2)*2:color=black,setsar=1"
    # Pick a mild random filter based on seed for reproducibility
    spices = [
        "eq=brightness=0.01:contrast=1.02",
        "unsharp=5:5:0.5",
        "gblur=sigma=0.3",
        "hue=h=2:s=1",
        "",
    ]
    idx = hash(seed) % len(spices) if seed else 0
    spice = spices[idx]
    vf_full = f"{vf},{spice}" if spice else vf
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_url,
        "-vf",
        vf_full,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-af",
        "volume=+0.5dB",
        "-movflags",
        "+faststart",
        output_path,
    ]
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"ffmpeg failed: {e.output.decode('utf-8', errors='ignore')}")


@app.post("/variant")
def create_variant(req: VariantRequest) -> Dict[str, str]:
    """Generate a perceptual fresh variant. Returns a CDN URL or local URL."""
    seed = req.seed or uuid.uuid4().hex
    tmp_filename = f"/tmp/{uuid.uuid4().hex}.mp4"
    run_ffmpeg(req.file_url, tmp_filename, seed)
    # Determine destination key
    key = f"{uuid.uuid4().hex}.mp4"
    # Attempt S3 upload if configured
    if s3_client and S3_BUCKET:
        try:
            s3_client.upload_file(tmp_filename, S3_BUCKET, key, ExtraArgs={"ContentType": "video/mp4"})
            # Compose CDN URL if provided
            if CDN_URL:
                url = f"{CDN_URL}/{key}"
            else:
                # If no CDN_URL is defined, use S3 HTTP endpoint
                url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"
            return {"cdn_url": url}
        except Exception as e:
            # Fall back to static serving on failure
            print(f"Warning: S3 upload failed, falling back to local static directory: {e}")
    # Fallback: copy to local static directory for serving
    dest = os.path.join(STATIC_DIR, key)
    shutil.copy2(tmp_filename, dest)
    return {"cdn_url": f"/static/{key}"}
