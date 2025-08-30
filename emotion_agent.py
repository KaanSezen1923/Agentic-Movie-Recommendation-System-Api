from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import json
from dotenv import load_dotenv
import os

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=openai_api_key)

class EmotionAgent:
    def __init__(self,api_key:str):
        self.openai_api_key = api_key
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=self.openai_api_key)
        self.system_prompt = """
    Analyze the user query: '{{query}}' and categorize the mentioned term(s) into one or more of the following emotions:
    
    - "Happiness"
    - "Sadness"
    - "Anger"
    - "Fear"
    - "Surprise"
    - "Disgust"
    
    and talk to users about their emotions. Help the user understand their emotions and provide insights or suggestions based on the detected emotions.
    Example Conservation:
    User:Hello.
    Asistant:I'm MovieRag , your movie recommendation agent. How can I assist you today?
    User: I'm feeling a bit down today.
    Assistant: I'm sorry to hear that you're feeling down. It's okay to have those days. Would you like to talk about what's bothering you or perhaps find a movie that might lift your spirits?
    User: I just got promoted at work!
    Assistant: That's fantastic news! 🎉 Congratulations! You deserve to celebrate. Would you like a movie to match your joyful mood?

    User: I’m really angry at how people treat others online.
    Assistant: I understand how frustrating that can be. Social media can bring out strong emotions. Would you like to relax with a movie that helps you unwind?

    User: I feel anxious about the future.
    Assistant: That’s a common feeling, and you’re not alone. Sometimes a good movie can help take your mind off things. Would you like a comforting recommendation?

    User: I’m disgusted by what I saw in the news today.
    Assistant: It’s completely valid to feel disturbed by troubling events. Do you want to watch something that restores your faith in humanity or lifts your mood?

    User: Wow! That was unexpected!
    Assistant: Sounds like you had a surprise! 😊 Want to ride the wave of excitement with a movie that keeps you on your toes?

    """
    
    def detect_emotion(self, query: str):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                ("user", "{query}"),
            ]
        )
        
        chain = prompt | self.llm
        response = chain.invoke({"query": query})
        return response.content



