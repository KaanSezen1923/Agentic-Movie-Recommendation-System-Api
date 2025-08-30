from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from neo4j import GraphDatabase
import json
from dotenv import load_dotenv
import os

load_dotenv()

class CategoryAgent:
    def __init__(self,api_key:str, neo4j_uri:str, neo4j_user:str, neo4j_password:str):
        self.llm= ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=api_key)
        self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.system_prompt ="""
    Analyze the user query: '{{query}}' and categorize the mentioned term(s) into one or more of the following categories:

    - "Director" (e.g., Christopher Nolan, Quentin Tarantino)
    - "Actor" (e.g., Leonardo DiCaprio, Tom Hanks)
    - "Genre" (e.g., 'Action', 'Adventure', 'Fantasy', 'Science Fiction', 'Crime', 'Drama', 'Thriller', 'Animation', 'Family', 'Western', 'Comedy', 'Romance', 'Horror', 'Mystery', 'History', 'War', 'Music', 'Documentary', 'Foreign', 'TV Movie')
    - "Keyword" (e.g., 'culture clash', 'future', 'space war', 'space colony', 'society', 'space travel', 'futuristic', 'romance', 'space', 'alien', 'tribe', 'alien planet', 'cgi', 'marine', 'soldier', 'battle', 'love affair', 'anti war', 'power relations', 'mind and soul', '3d', 'ocean', 'drug abuse', 'exotic island', 'east india trading company', "love of one's life", 'traitor', 'shipwreck', 'strong woman', 'ship', 'alliance', 'calypso', 'afterlife', 'fighter', 'pirate', 'swashbuckler', 'aftercreditsstinger', 'spy', 'based on novel', 'secret agent', 'sequel', 'mi6', 'british secret service', 'united kingdom', 'dc comics', 'crime fighter', 'terrorist', 'secret identity', 'burglar', 'hostage drama', 'time bomb', 'gotham city', 'vigilante', 'cover-up', 'superhero', 'villainess', 'tragic hero', 'terrorism', 'destruction', 'catwoman', 'cat burglar', 'imax', 'flood', 'criminal underworld', 'batman', 'mars', 'medallion', 'princess', 'steampunk', 'martian', 'escape', 'edgar rice burroughs', 'alien race', 'superhuman strength', 'mars civilization', 'sword and planet', '19th century', 'dual identity', 'amnesia', 'sandstorm', 'forgiveness', 'spider', 'wretch', 'death of a friend', 'egomania', 'sand', 'narcism', 'hostility', 'marvel comic', 'revenge', 'hostage', 'magic', 'horse', 'fairy tale', 'musical', 'animation', 'tower', 'blonde woman', 'selfishness', 'healing power', 'based on fairy tale', 'duringcreditsstinger', 'healing gift', 'animal sidekick', 'based on comic book', 'vision', 'superhero team', 'marvel cinematic universe', 'witch', 'broom', 'school of witchcraft', 'wizardry', 'apparition', 'teenage crush', 'werewolf', 'super powers','vampire')
    - "Movie" (e.g., Inception, Interstellar)
    
    Expected Output :
    
    The output should be a JSON object with the keys "Category" and "Name". If multiple categories apply, return them as a comma-separated list in the "Category" field. The "Name" field should contain the name of the entity or term mentioned in the query.
"""
        self.query_map = {
            "Actor": """MATCH (a:Actor)-[:ACTED_IN]->(m:Movie) WHERE toLower(a.name) 
            CONTAINS toLower($param) RETURN m.movie_id, m.title, m.overview,m.genres,m.actors,m.director, m.vote_average,m.image_path LIMIT 10""",
            "Director": """MATCH (d:Director)-[:DIRECTED]->(m:Movie) WHERE toLower(d.name) 
            CONTAINS toLower($param) RETURN m.movie_id, m.title, m.overview,m.genres,m.actors,m.director, m.vote_average,m.image_path LIMIT 10""",
            "Genre": """MATCH (g:Genre)-[:HAS_GENRE]->(m:Movie) WHERE toLower(g.name) 
            CONTAINS toLower($param) RETURN m.movie_id, m.title, m.overview,m.genres,m.actors,m.director, m.vote_average,m.image_path LIMIT 10""",
            "Keyword": """MATCH (k:Keyword)-[:HAS_KEYWORD]->(m:Movie) WHERE toLower(k.name) 
            CONTAINS toLower($param) RETURN m.movie_id, m.title, m.overview,m.genres,m.actors,m.director, m.vote_average,m.image_path LIMIT 10""",
            "Movie": """MATCH (m:Movie) WHERE toLower(m.title) CONTAINS toLower($param) 
            WITH m MATCH (similar:Movie) WHERE toLower(similar.overview) CONTAINS toLower(m.overview) 
            RETURN similar.movie_id, similar.title, similar.overview, similar.vote_average LIMIT 10"""
        } 
        
        self.categories=[]
        self.names=[]
        

        
    def category_agent(self, query:str):
        self.prompt = ChatPromptTemplate.from_messages(
        [
            ("system", self.system_prompt),
            ("user", "{query}"),
        ])
        self.chain= self.prompt | self.llm
        response = self.chain.invoke({"query": query})
        json_response = json.loads(response.content)
        category = json_response.get("Category", "Unknown")
        name = json_response.get("Name", "Unknown")
        categories = category.split(",") if category else []
        names = name.split(",") if name else []
        categories = [cat.strip() for cat in categories if cat.strip()]
        names = [n.strip() for n in names if n.strip()]
        #print("Categories:", categories)
        #print("Names:", names)
        self.categories = categories
        self.names = names
        results=[]
        for i in range(len(self.categories)):
            query = self.query_map.get(self.categories[i])
            if not query:
                continue
    
            res = self.neo4j_query(self.categories[i], self.names[i])
            results.append({"category": self.categories[i], "name": self.names[i], "results": res})
        return results
    
    def neo4j_query(self,category:str, name:str):
            query = self.query_map.get(category)
            if not query:
                return []
            with self.neo4j_driver.session() as session:
                #print(f"Running query for category: {category} with name: {name}")
                res = session.run(query, {"param": name}).data()
                return res
            
    def close(self):
        if self.neo4j_driver:
            self.neo4j_driver.close()



        



        




            
            

  

    

    