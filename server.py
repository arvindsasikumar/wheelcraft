"""Single entry point. Starts the wheel pipeline + the FastAPI server."""

import os
import sys

# In PyInstaller --windowed builds, Windows doesn't allocate a console, so
# sys.stdin/stdout/stderr are None. Libraries that introspect them (notably
# uvicorn's default log formatter calling .isatty()) crash. Replace them with
# devnull file objects BEFORE any such import.
if getattr(sys, "frozen", False):
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r")

import asyncio
import logging
import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from wheelmap.pipeline import WheelPipeline
from wheelmap.profile import Profile
from wheelmap.store import ProfileStore, safe_name


PORT = 8765
URL = f"http://localhost:{PORT}"


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
    if os.environ.get("WHEELCRAFT_NO_BROWSER") != "1":
        # Tiny delay so uvicorn finishes binding before the browser hits the URL.
        threading.Timer(0.8, lambda: webbrowser.open(URL)).start()
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


@app.post("/api/shutdown")
def shutdown() -> dict:
    """Stop the server. Used by the UI's Quit button."""
    threading.Timer(0.3, lambda: os._exit(0)).start()
    return {"ok": True}


def main() -> int:
    if getattr(sys, "frozen", False):
        log_file = PROFILES.parent / "wheelcraft.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    try:
        import uvicorn

        uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
    except Exception:
        logging.exception("server crashed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
