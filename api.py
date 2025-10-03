from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from manager_agent import ManagerAgent
import os
import requests


app = FastAPI()
load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # İstersen buraya ["http://localhost:3000", "https://seninfrontend.com"] da yazabilirsin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


openai_api_key = os.getenv("OPENAI_API_KEY")
tmdb_api_key = os.getenv("TMDB_API_KEY")
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
username= os.getenv("FIREBASE_USERNAME", "default_user")
manager_agent = ManagerAgent(openai_api_key, neo4j_uri, neo4j_user, neo4j_password,username=username)

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
    

@app.get("/process_query/{query}", response_model=AgentResponse)
def agent(query: str):
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    response = manager_agent.process_query(query)
    
    if not response:
        raise HTTPException(status_code=500, detail="No response from the model")
    
    return response

@app.get("/get_trailer/{movie_title}", response_model=MovieTrailerResponse)
def get_movie_trailer(movie_title:str):
    
    if not movie_title:
        raise HTTPException(status_code=400, detail="Movie movie_title cannot be empty")
    
    url1= f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={movie_title}&language=en-US"
    response = requests.get(url1)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            movie = data['results'][0]
            movie_id = movie['id']
    
            url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?language=en-US"

            headers = {
                "accept": "application/json",
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJkNGQ4OTlmNDY4MGQ4ZGZmZmExODk3MmEwZWNhYTcyOCIsIm5iZiI6MTY4NzI4MDMwMC45NDEsInN1YiI6IjY0OTFkYWFjMjYzNDYyMDE0ZTU5YzZlZiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.bzAjIfieM-JBQSCDG3JQzn56-BMq40Y8NF6TJjPO1lg"
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for video in data.get('results', []):
                    print(video)
                    if video['type'] == 'Trailer':
                        trailer_url= f"https://www.youtube.com/watch?v={video['key']}"
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
        if data['results']:
            movie = data['results'][0]
            image_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
            return MovieImageResponse(image_url=image_url)
    else:
        raise HTTPException(status_code=response.status_code, detail="Error fetching movie image")
    

    
        

