"""
VocabMaster Server — FastAPI backend with JWT auth + data sync
Run: uvicorn server:app --host 0.0.0.0 --port 8000
"""
import os, hashlib, json, logging
from pathlib import Path
from datetime import datetime, timedelta

import jwt
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiosqlite

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vocabmaster")

app = FastAPI(title="VocabMaster API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = Path(os.environ.get("VOCABMASTER_DB", "/data/vocabmaster.db"))
JWT_SECRET = os.environ.get("JWT_SECRET", "vocabmaster-dev-secret-change-in-production")
JWT_EXPIRE_DAYS = 30

# ─── Database ─────────────────────────────────────────────
async def get_db():
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    return db

async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS user_data (
            user_id INTEGER PRIMARY KEY,
            words TEXT DEFAULT '{}',
            stats TEXT DEFAULT '{}',
            version INTEGER DEFAULT 2,
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)
    await db.commit()
    await db.close()
    logger.info("Database initialized")

@app.on_event("startup")
async def startup():
    await init_db()

# ─── Auth Helpers ─────────────────────────────────────────
def hash_password(pw: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100000)
    return salt.hex() + ":" + key.hex()

def verify_password(pw: str, hashed: str) -> bool:
    salt_hex, key_hex = hashed.split(":")
    key = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt_hex), 100000)
    return key.hex() == key_hex

def create_token(user_id: int) -> str:
    return jwt.encode(
        {"user_id": user_id, "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)},
        JWT_SECRET, algorithm="HS256"
    )

def decode_token(token: str) -> int:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])["user_id"]

async def get_current_user(request: Request) -> int:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    try:
        return decode_token(auth[7:])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except Exception:
        raise HTTPException(401, "Invalid token")

# ─── Models ───────────────────────────────────────────────
class AuthRequest(BaseModel):
    username: str
    password: str

class SyncData(BaseModel):
    words: dict = {}
    stats: dict = {}
    version: int = 2

# ─── Auth Routes ──────────────────────────────────────────
HARDCODED_USER = "kousi"
HARDCODED_PASS = "00000"

@app.post("/api/register")
async def register(body: AuthRequest):
    raise HTTPException(403, "Registration is disabled")

@app.post("/api/login")
async def login(body: AuthRequest):
    if body.username == HARDCODED_USER and body.password == HARDCODED_PASS:
        token = create_token(0)
        logger.info(f"LOGIN: hardcoded user '{HARDCODED_USER}' (user_id=0)")
        return {"token": token, "user_id": 0, "username": HARDCODED_USER}
    db = await get_db()
    try:
        user = await db.execute("SELECT * FROM users WHERE username = ?", (body.username,))
        user = await user.fetchone()
        if not user or not verify_password(body.password, user["password_hash"]):
            raise HTTPException(401, "Invalid credentials")
        logger.info(f"LOGIN: db user '{body.username}' (user_id={user['id']})")
        return {"token": create_token(user["id"]), "user_id": user["id"], "username": user["username"]}
    finally:
        await db.close()

# ─── Sync Routes ──────────────────────────────────────────
@app.get("/api/sync/download")
async def sync_download(user_id: int = Depends(get_current_user)):
    db = await get_db()
    try:
        row = await db.execute("SELECT * FROM user_data WHERE user_id = ?", (user_id,))
        row = await row.fetchone()
        if not row:
            logger.info(f"SYNC DOWNLOAD user_id={user_id}: no data yet")
            return {"words": {}, "stats": {}, "version": 2}
        words = json.loads(row["words"])
        stats = json.loads(row["stats"])
        logger.info(f"SYNC DOWNLOAD user_id={user_id}: {len(words)} words, {stats.get('totalReviews',0)} reviews, updated={row['updated_at']}")
        return {"words": words, "stats": stats, "version": row["version"], "updated_at": row["updated_at"]}
    finally:
        await db.close()

@app.post("/api/sync/upload")
async def sync_upload(data: SyncData, user_id: int = Depends(get_current_user)):
    db = await get_db()
    try:
        words_json = json.dumps(data.words, ensure_ascii=False)
        stats_json = json.dumps(data.stats, ensure_ascii=False)
        word_count = len(data.words)
        review_count = data.stats.get("totalReviews", 0)
        await db.execute(
            "INSERT INTO user_data (user_id, words, stats, version, updated_at) VALUES (?, ?, ?, ?, datetime('now')) "
            "ON CONFLICT(user_id) DO UPDATE SET words=excluded.words, stats=excluded.stats, version=excluded.version, updated_at=datetime('now')",
            (user_id, words_json, stats_json, data.version)
        )
        await db.commit()
        logger.info(f"SYNC UPLOAD user_id={user_id}: saved {word_count} words, {review_count} reviews")
        
        # Verify write
        row = await db.execute("SELECT words, stats FROM user_data WHERE user_id = ?", (user_id,))
        row = await row.fetchone()
        verify_words = len(json.loads(row["words"])) if row else 0
        logger.info(f"SYNC VERIFY user_id={user_id}: DB now has {verify_words} words")
        
        return {"status": "ok", "word_count": word_count, "review_count": review_count}
    finally:
        await db.close()

@app.get("/api/me")
async def me(user_id: int = Depends(get_current_user)):
    db = await get_db()
    try:
        user = await db.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,))
        row = await user.fetchone()
        if row:
            return dict(row)
        return {"id": user_id, "username": HARDCODED_USER if user_id == 0 else "unknown"}
    finally:
        await db.close()

# ─── Debug / Health ───────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "db": str(DB_PATH), "db_exists": DB_PATH.exists()}

@app.get("/api/debug/db")
async def debug_db(user_id: int = Depends(get_current_user)):
    """查看自己的数据库数据（调试用）"""
    db = await get_db()
    try:
        row = await db.execute("SELECT user_id, updated_at, length(words) as words_len, length(stats) as stats_len FROM user_data WHERE user_id = ?", (user_id,))
        row = await row.fetchone()
        if not row:
            return {"user_id": user_id, "data": None, "message": "No data row"}
        return {
            "user_id": row["user_id"],
            "updated_at": row["updated_at"],
            "words_bytes": row["words_len"],
            "stats_bytes": row["stats_len"]
        }
    finally:
        await db.close()

# ─── Static ───────────────────────────────────────────────
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

@app.get("/")
async def root():
    idx = static_dir / "index.html"
    return FileResponse(idx) if idx.exists() else {"message": "VocabMaster API", "docs": "/docs"}

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
