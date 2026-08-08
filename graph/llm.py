from langchain_groq import ChatGroq
from graph.config import GROQ_API_KEY

def get_llm(temperature: float = 0.3) -> ChatGroq:
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=GROQ_API_KEY,
        temperature=temperature,
        max_retries=2,
        timeout=30,
    )