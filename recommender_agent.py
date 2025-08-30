from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from category_agent import CategoryAgent
from emotion_agent import EmotionAgent

import json
from dotenv import load_dotenv
import os

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")


class RecommenderAgent:
    def __init__(self, api_key: str):
        self.openai_api_key = api_key
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=self.openai_api_key)
        self.system_prompt = """
        You are MovieRage, a movie recommendation agent. Your task is to recommend movies based on the {query} and the {context} provided.
        The context includes information about the user's preferences, emotions, and any other relevant details that can help you make a personalized recommendation.
        You at least 5 movies based on the user's query and context. Each movie should be represented as a JSON object with the following structure:
        Analyze the query and context, and provide a JSON response with the following structure:
        Title: The title of the recommended movie.
        Director: The director of the movie.
        Star Cast: A list of main actors in the movie.
        Genre: The genre of the movie.
        Overview: A brief summary of the movie's plot.
        Reason: A brief explanation of why this movie is recommended based on the query and context.
        Image URL: A URL to an image of the movie poster.
        Example Output:
        
        [{{
            "Title": "Inception",
            "Director": "Christopher Nolan",
            "Star Cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"],
            "Genre": "Science Fiction",
            "Overview": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a CEO.",
            "Reason": "This movie is recommended because it combines elements of science fiction and psychological thriller, which aligns with the user's interest in complex narratives.",
            "Image URL": "https://example.com/inception.jpg"
            
            "Title": "Interstellar",
            "Director": "Christopher Nolan",
            "Star Cast": ["Matthew McConaughey", "Anne Hathaway", "Jessica Chastain"],
            "Genre": "Science Fiction",
            "Overview": "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
            "Reason": "This movie is recommended because it combines elements of science fiction and psychological thriller, which aligns with the user's interest in complex narratives.",
            "Image URL": "https://example.com/interstellar.jpg"
            
            "Title": "Prestige",
            "Director": "Christopher Nolan",
            "Star Cast": ["Christian Bale", "Hugh Jackman", "Scarlett Johansson"],
            "Genre": "Science Fiction",
            "Overview": "After a tragic accident, two stage magicians engage in a battle to create the ultimate illusion while sacrificing everything they have to outwit each other.",
            "Reason": "This movie is recommended because it combines elements of science fiction and psychological thriller, which aligns with the user's interest in complex narratives.",
            "Image URL": "https://example.com/prestige.jpg"
            
            "Title": "Batman Dark Knight",
            "Director": "Christopher Nolan",
            "Star Cast": ["Christian Bale", "Heath Ledger", "Aaron Eckhart"],
            "Genre": "Crime, Drama, Action",
            "Overview": "When the menace known as the Joker emerges from his mysterious past, he wreaks havoc and chaos on the people of Gotham. The Dark Knight must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
            "Reason": "This movie is recommended because it combines elements of crime, drama, and action, which aligns with the user's interest in complex narratives.",
            "Image URL": "https://example.com/dark_knight.jpg"
            
            "Title": Memento",
            "Director": "Christopher Nolan",
            "Star Cast": ["Guy Pearce", "Carrie-Anne Moss", "Joe Pantoliano"],
            "Genre": "Mystery, Thriller",
            "Overview": "a man suffering from short-term memory loss uses notes and tattoos to hunt for revenge against the person he thinks killed his wife.",
            "Reason": "This movie is recommended because it combines elements of mystery and thriller, which aligns with the user's interest in complex narratives.",
            "Image URL": "https://example.com/memento.jpg"
            
            
            
        }}
        ]
        
        DO NOT use markdown, bullets, natural language text, or any explanation outside JSON.
        

        
        
        Ensure that the recommendation is relevant to the user's query and context, and provide a well-rounded explanation for your choice.
        
        
        """
    
    def recommend(self, query: str,movie_context):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                ("user", "{query}"),
            ]
        )

        chain = prompt | self.llm
        try:
            response = chain.invoke({"query": query, "context": movie_context})

            if not hasattr(response, "content") or not response.content.strip():
                print("❌ Uyarı: LLM cevabı boş geldi.")
                return {"error": "LLM returned empty content."}

            

            recommendations = json.loads(response.content)
            return recommendations
        except json.JSONDecodeError as je:
            print("❌ JSON decode hatası:", je)
            print("🔍 LLM yanıtı (muhtemelen düzgün JSON değil):", getattr(response, "content", "BOŞ"))
            return {"error": "Invalid JSON response from LLM"}
        except Exception as e:
            print("⚠️ Genel hata:", str(e))
            return {"error": "Unexpected error in recommend()"}
    
    

        
   

    
    

    