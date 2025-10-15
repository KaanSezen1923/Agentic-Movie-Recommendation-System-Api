from datetime import datetime
import hashlib
import os
import secrets
from typing import List, Optional
import base64
import firebase_admin
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, firestore
from pydantic import BaseModel, EmailStr, Field
from dotenv import load_dotenv

from manager_agent import ManagerAgent
import requests

app = FastAPI()
load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://movierag.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai_api_key = os.getenv("OPENAI_API_KEY")
tmdb_api_key = os.getenv("TMDB_API_KEY")
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
username = os.getenv("FIREBASE_USERNAME", "default_user")
manager_agent = ManagerAgent(openai_api_key, neo4j_uri, neo4j_user, neo4j_password, username=username)

def ensure_firebase_credentials_file():
    base64_str = os.getenv("FIREBASE_CREDENTIAL_BASE64")
    cred_path = os.getenv("FIREBASE_CREDENTIAL_PATH", "firebase.json")
    if base64_str and not os.path.exists(cred_path):
        with open(cred_path, "wb") as f:
            f.write(base64.b64decode(base64_str))
    return cred_path

FIREBASE_CREDENTIAL_PATH = ensure_firebase_credentials_file()


class AgentResponse(BaseModel):
    mode: str
    categories: Optional[List[dict]] = None
    profile: Optional[str] = None
    recommendations: Optional[List[dict]] = None
    emotion_response: Optional[str] = None


class MovieTrailerResponse(BaseModel):
    trailer_url: str


class MovieImageResponse(BaseModel):
    image_url: str


class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    message: str
    username: Optional[str] = None
    email: Optional[EmailStr] = None


class ChatMessage(BaseModel):
    id: Optional[str] = None
    role: str
    text: Optional[str] = None
    recommendations: Optional[List[dict]] = None
    isLoading: Optional[bool] = None
    isError: Optional[bool] = None


class ChatSessionPayload(BaseModel):
    id: str
    title: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)


def get_firestore_client() -> firestore.Client:
    if not firebase_admin._apps:
        cred_path = FIREBASE_CREDENTIAL_PATH
        if not os.path.isabs(cred_path):
            cred_path = os.path.join(os.path.dirname(__file__), cred_path)
        if not os.path.exists(cred_path):
            raise HTTPException(status_code=500, detail="Firebase credential file not found")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if salt is None:
        salt_bytes = secrets.token_bytes(16)
        salt = salt_bytes.hex()
    else:
        try:
            salt_bytes = bytes.fromhex(salt)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="Stored password salt is invalid") from exc
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 100_000).hex()
    return salt, hashed


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    _, computed_hash = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, password_hash)


def get_chats_collection(username: str):
    db = get_firestore_client()
    return db.collection("users").document(username).collection("chats")


def serialize_chat_document(doc) -> dict:
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return data

@app.get("/")
def root():
    return {"status": "ok"}



@app.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    db = get_firestore_client()
    users_ref = db.collection("users")

    if users_ref.document(payload.username).get().exists:
        raise HTTPException(status_code=409, detail="Username is already in use")

    email_query = list(users_ref.where("email", "==", payload.email).limit(1).stream())
    if email_query:
        raise HTTPException(status_code=409, detail="Email is already registered")

    salt, password_hash = hash_password(payload.password)

    users_ref.document(payload.username).set(
        {
            "email": payload.email,
            "password_salt": salt,
            "password_hash": password_hash,
            "created_at": datetime.utcnow().isoformat(),
            "last_login_at": None,
        }
    )

    return AuthResponse(message="Signup successful", username=payload.username, email=payload.email)


@app.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    db = get_firestore_client()
    users_ref = db.collection("users")

    user_doc = next(users_ref.where("email", "==", payload.email).limit(1).stream(), None)
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_data = user_doc.to_dict() or {}
    password_salt = user_data.get("password_salt")
    password_hash = user_data.get("password_hash")

    if not password_salt or not password_hash:
        raise HTTPException(status_code=500, detail="Stored credentials are incomplete")

    if not verify_password(payload.password, password_salt, password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    try:
        users_ref.document(user_doc.id).update({"last_login_at": datetime.utcnow().isoformat()})
    except Exception:
        pass

    return AuthResponse(message="Login successful", username=user_doc.id, email=payload.email)


@app.get("/users/{username}/chats", response_model=List[ChatSessionPayload])
def list_chats(username: str):
    chats_ref = get_chats_collection(username)
    chats = [serialize_chat_document(doc) for doc in chats_ref.stream()]
    return chats


@app.post("/users/{username}/chats", response_model=ChatSessionPayload)
def create_chat(username: str, payload: ChatSessionPayload):
    chats_ref = get_chats_collection(username)
    now_iso = datetime.utcnow().isoformat()
    data = payload.dict(exclude_none=True)
    data.setdefault("createdAt", now_iso)
    data.setdefault("updatedAt", now_iso)
    chat_id = data.pop("id")
    chats_ref.document(chat_id).set(data)
    return ChatSessionPayload(id=chat_id, **data)


@app.put("/users/{username}/chats/{chat_id}", response_model=ChatSessionPayload)
def upsert_chat(username: str, chat_id: str, payload: ChatSessionPayload):
    chats_ref = get_chats_collection(username)
    if payload.id != chat_id:
        raise HTTPException(status_code=400, detail="Chat ID mismatch")
    data = payload.dict(exclude={"id"}, exclude_none=True)
    if "updatedAt" not in data:
        data["updatedAt"] = datetime.utcnow().isoformat()
    chats_ref.document(chat_id).set(data, merge=True)
    return ChatSessionPayload(id=chat_id, **data)


@app.delete("/users/{username}/chats/{chat_id}")
def delete_chat(username: str, chat_id: str):
    chats_ref = get_chats_collection(username)
    chats_ref.document(chat_id).delete()
    return {"status": "deleted"}


@app.get("/process_query/{query}", response_model=AgentResponse)
def agent(query: str):
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    response = manager_agent.process_query(query)

    if not response:
        raise HTTPException(status_code=500, detail="No response from the model")

    return response


@app.get("/get_trailer/{movie_title}", response_model=MovieTrailerResponse)
def get_movie_trailer(movie_title: str):
    if not movie_title:
        raise HTTPException(status_code=400, detail="Movie title cannot be empty")

    url_search = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={movie_title}&language=en-US"
    response = requests.get(url_search)
    if response.status_code == 200:
        data = response.json()
        if data.get("results"):
            movie = data["results"][0]
            movie_id = movie["id"]
            url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?language=en-US"

            headers = {
                "accept": "application/json",
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJkNGQ4OTlmNDY4MGQ4ZGZmZmExODk3MmEwZWNhYTcyOCIsIm5iZiI6MTY4NzI4MDMwMC45NDEsInN1YiI6IjY0OTFkYWFjMjYzNDYyMDE0ZTU5YzZlZiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.bzAjIfieM-JBQSCDG3JQzn56-BMq40Y8NF6TJjPO1lg",
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for video in data.get("results", []):
                    if video.get("type") == "Trailer":
                        trailer_url = f"https://www.youtube.com/watch?v={video['key']}"
                        return MovieTrailerResponse(trailer_url=trailer_url)
            else:
                print(f"Error fetching trailer: {response.status_code}")


@app.get("/get_image/{movie_title}", response_model=MovieImageResponse)
def get_movie_image(movie_title: str):
    if not movie_title:
        raise HTTPException(status_code=400, detail="Movie title cannot be empty")

    url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={movie_title}&language=en-US"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data.get("results"):
            movie = data["results"][0]
            image_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
            return MovieImageResponse(image_url=image_url)
    else:
        raise HTTPException(status_code=response.status_code, detail="Error fetching movie image")
    

    
        




