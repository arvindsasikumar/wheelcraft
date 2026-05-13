"""Single entry point. Starts the wheel pipeline + the FastAPI server."""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from wheelmap.pipeline import WheelPipeline
from wheelmap.profile import Profile
from wheelmap.store import ProfileStore, safe_name


if getattr(sys, "frozen", False):
    # PyInstaller bundle: static lives in the bundle, profiles in user appdata.
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    STATIC = BUNDLE_DIR / "static"
    PROFILES = Path(os.environ.get("APPDATA", str(Path.home()))) / "wheelcraft" / "profiles"
else:
    HERE = Path(__file__).parent
    STATIC = HERE / "static"
    PROFILES = HERE / "profiles"

store = ProfileStore(PROFILES)
_active_name = store.get_active_name()
pipeline = WheelPipeline(profile=store.load(_active_name))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    pipeline.start()
    yield
    pipeline.stop()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.websocket("/live")
async def live(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            await ws.send_json(pipeline.snapshot_dict())
            await asyncio.sleep(1 / 60)
    except WebSocketDisconnect:
        return


@app.get("/api/profiles")
def list_profiles() -> dict:
    return {"profiles": store.list_names(), "active": pipeline.profile.name}


@app.get("/api/profiles/{name}")
def get_profile(name: str) -> dict:
    try:
        return store.load(name).model_dump()
    except FileNotFoundError:
        raise HTTPException(404, f"profile {name!r} not found")


@app.put("/api/profiles/{name}")
def put_profile(name: str, profile: Profile) -> dict:
    safe_name(name)
    if profile.name != name:
        raise HTTPException(400, "profile.name does not match path name")
    store.save(profile)
    if pipeline.profile.name == name:
        pipeline.set_profile(profile)
    return {"ok": True}


@app.post("/api/profiles/active")
def update_active(profile: Profile) -> dict:
    """Live-edit the active profile in memory (not persisted)."""
    if profile.name != pipeline.profile.name:
        raise HTTPException(400, "profile.name does not match active profile")
    pipeline.set_profile(profile)
    return {"ok": True}


@app.post("/api/profiles/{name}/activate")
def activate(name: str) -> dict:
    try:
        profile = store.load(name)
    except FileNotFoundError:
        raise HTTPException(404, name)
    pipeline.set_profile(profile)
    store.set_active_name(name)
    return {"ok": True, "active": name}


@app.delete("/api/profiles/{name}")
def delete_profile(name: str) -> dict:
    try:
        store.delete(name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if pipeline.profile.name == name:
        default = store.load("default")
        pipeline.set_profile(default)
        store.set_active_name("default")
    return {"ok": True}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
