import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI


_ = load_dotenv()

def load_llm(provider: str):
    if provider == "groq":
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise RuntimeError("❌ GROQ_API_KEY not found in .env")
        return ChatGroq(model="moonshotai/kimi-k2-instruct-0905", temperature=0)

    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("❌ OPENAI_API_KEY not found in .env")
        return ChatOpenAI(model="gpt-4o-mini", temperature=0)

    if provider == "claude":
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("❌ ANTHROPIC_API_KEY not found in .env")
        return ChatAnthropic(model="claude-haiku-4-5", temperature=0)

    if provider == "gemini":
        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("❌ GOOGLE_API_KEY not found in .env")
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)

    raise ValueError("Unsupported model provider")