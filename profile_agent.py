import firebase_admin
from firebase_admin import credentials, initialize_app
from firebase_admin import firestore
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os 

load_dotenv()

class ProfileAgent:
    def __init__(self, api_key: str):
        self.openai_api_key = api_key
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=self.openai_api_key)
        self.system_prompt = """You are a movie preference classification agent. Your task is to analyze past user queries and extract a comprehensive user profile based on their movie preferences.

        EXTRACTION TARGETS:
        - Most frequently requested movie genres (prioritize top 2-3)
        - Preferred directors (identify top 2-3 most mentioned)
        - Favorite actors/actresses (identify top 2-3 most mentioned)
        - Recurring keywords/themes (extract 3-5 descriptive terms)

        ANALYSIS GUIDELINES:
        1. Count frequency of mentions across all queries
        2. Identify patterns in user language and preferences
        3. Prioritize explicit preferences over implicit ones
        4. Handle variations in naming (e.g., "Nolan" vs "Christopher Nolan")
        5. Extract thematic keywords that capture the user's taste profile

        OUTPUT FORMAT:
        Return a single structured string in this exact format:
        "Preferred genres: [genre1, genre2]; Top directors: [director1, director2]; Favorite actors: [actor1, actor2]; Key themes: [keyword1, keyword2, keyword3]"

        EXAMPLE:
        Input queries mentioning: "action movies", "Christopher Nolan films", "Leonardo DiCaprio", "thrilling plots", "mind-bending stories"
        Output: "Preferred genres: Action, Thriller; Top directors: Christopher Nolan; Favorite actors: Leonardo DiCaprio; Key themes: mind-bending, thrilling, complex-plots"

        EDGE CASES:
        - If insufficient data for any category, return "Not enough data"
        - If user shows equal preference for multiple items, list up to 3 maximum
        - Normalize similar terms (e.g., "sci-fi" and "science fiction" → "Science Fiction")
        """
    def extract_profile(self, context: list):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                ("user", "{context}"),
            ]
        )
        
        chain = prompt | self.llm
        response = chain.invoke({"context": context})
        return response.content





            
