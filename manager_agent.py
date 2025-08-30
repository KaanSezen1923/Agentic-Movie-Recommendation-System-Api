from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from category_agent import CategoryAgent
from emotion_agent import EmotionAgent
from recommender_agent import RecommenderAgent
from profile_agent import ProfileAgent
import firebase_admin
from firebase_admin import credentials, initialize_app
from firebase_admin import firestore
from neo4j import GraphDatabase
import json
from dotenv import load_dotenv
import os

load_dotenv()


class ManagerAgent:
    def __init__(self, api_key: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str,username: str = None):
        self.openai_api_key = api_key
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=self.openai_api_key)
        self.category_agent = CategoryAgent(self.openai_api_key, neo4j_uri, neo4j_user, neo4j_password)
        self.emotion_agent = EmotionAgent(self.openai_api_key)
        self.recommender_agent = RecommenderAgent(self.openai_api_key)
        self.profile_agent = ProfileAgent(self.openai_api_key)
        self.username = username
        

    def process_query(self, query: str):
        

        
        category_result = self.category_agent.category_agent(query)
        context= self.get_chats_from_firebase(self.username)
        profile_result = self.profile_agent.extract_profile(context)
        movie_context=category_result + [profile_result]
        
        if category_result and any(c.get("results") for c in category_result):
            
            print("🔍 Category detected. Getting movie recommendations...")
            recommendations = self.recommender_agent.recommend(query, movie_context)
            return {
                    "mode": "category",
                    "categories": category_result,
                    "profile": profile_result,
                    "recommendations": recommendations
            }
        else:
                
            print("💬 No specific category found. Engaging emotion agent...")
            emotion_response = self.emotion_agent.detect_emotion(query)
            return {
                    "mode": "emotion",
                    "emotion_response": emotion_response
            }
            
    def get_chats_from_firebase(self,username:str):
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate("firebase.json")
                firebase_admin.initialize_app(cred)
            except Exception as e:
                return (f"Firebase başlatma hatası: {e}")

        db = firestore.client()
        try:
            chat_histories = {}
            chats_ref = db.collection("users").document(username).collection("chats")
            for chat_doc in chats_ref.stream():
                chat_histories[chat_doc.id] = chat_doc.to_dict().get("messages", [])
            context = []
            for chat_id, messages in chat_histories.items():
                for message in messages:
                    if message.get("role") == "user":
                        context.append(message.get("content"))
            return context
        except Exception as e:
            
            return {}

            


    