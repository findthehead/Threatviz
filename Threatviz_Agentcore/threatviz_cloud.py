import uuid
import boto3
from dotenv import load_dotenv
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from langgraph_checkpoint_aws import AgentCoreMemoryStore, AgentCoreMemorySaver
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain.agents.middleware import AgentMiddleware, AgentState
import json
import os
import requests
from rag import retrieve_framework_context
import uuid

_ = load_dotenv()
agentcore_app = BedrockAgentCoreApp()
MEMORY_ID = f"threatviz_mem-mtF65JAWeJ"
REGION = "us-east-1"
checkpointer = AgentCoreMemorySaver(memory_id=MEMORY_ID)
store = AgentCoreMemoryStore(memory_id=MEMORY_ID)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")



@tool
def fetch_cve(cve):
    """Extract the CVE syntaxt only and fetch full threat analysys about a CVE.
    Always use the tool when the user asks questions about CVE.
    Args:
        cve: Extract the CVE ID only from user conversation and some time may or may not include the cve ID which is bare minimum to start the analysis.
        If user doesn't give in first instance ask again for the correct CVE ID
        Get the CVE in CVE-XXXX-XXXX format and run the tool.
        
    Returns:
        Make sure you dont change anything , just elloborate the details to the user
    """
    url = f"https://cveawg.mitre.org/api/cve/{cve}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        res = response.json()
    return res

@tool
def fetch_rag():
    """Use this tool to analyze the CVE further with PASTA and STRIDE threatmodeling framework and Mermaid syntax, make sure you correclty structure the framework context with the user provided CVE which will help the user"""
    query = 'PASTA and STRIDE framework, Syntax reference / basics: Mermaid Syntax Reference\nSequence diagrams: Sequence Diagram\nClass diagrams: Class Diagram\nState diagrams: State Diagram\nEntity-relationship diagrams: ER Diagram\nPie charts: Pie Diagram\nC4 / Architecture diagrams: C4 Diagram\nArchitecture diagrams: Architecture'
    DOCS = retrieve_framework_context(query, k=5)
    return DOCS


tools = [fetch_cve, fetch_rag]


class MemoryMiddleware(AgentMiddleware):
    # Pre-model hook: saves messages and retrieves long-term memories
    def pre_model_hook(self, state: AgentState, config: RunnableConfig, *, store: BaseStore):
        """
        Hook that runs before LLM invocation to:
        1. Save the latest human message to long-term memory
        2. Retrieve relevant user preferences and memories
        3. Append memories to the context
        """
        actor_id = config["configurable"]["actor_id"]
        thread_id = config["configurable"]["thread_id"]
        
        # Namespace for this specific session
        namespace = (actor_id, thread_id)
        messages = state.get("messages", [])
        
        # Save the last human message to long-term memory
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                store.put(namespace, str(uuid.uuid4()), {"message": msg})
                
                # OPTIONAL: Retrieve user preferences from long-term memory
                # Search across all sessions for this actor
                user_preferences_namespace = ("preferences", actor_id)
                try:
                    preferences = store.search(
                        user_preferences_namespace, 
                        query=msg.content, 
                        limit=5
                    )
                    
                    # If we found relevant memories, add them to the context
                    if preferences:
                        memory_context = "\n".join([
                            f"Memory: {item.value.get('message', '')}" 
                            for item in preferences
                        ])
                        # You can append this to the messages or use it another way
                        print(f"Retrieved memories: {memory_context}")
                except Exception as e:
                    print(f"Memory retrieval error: {e}")
                break
        
        return {"messages": messages}


    # OPTIONAL: Post-model hook to save AI responses
    def post_model_hook(self, state, config: RunnableConfig, *, store: BaseStore):

        """
        Hook that runs after LLM invocation to save AI messages to long-term memory
        """
        actor_id = config["configurable"]["actor_id"]
        thread_id = config["configurable"]["thread_id"]
        namespace = (actor_id, thread_id)
        
        messages = state.get("messages", [])
        
        # Save the last AI message
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                store.put(namespace, str(uuid.uuid4()), {"message": msg})
                break
        
        return state

llm = init_chat_model(
    model="openai/gpt-oss-20b", 
    model_provider="groq",
    api_key=GROQ_API_KEY
)


system_prompt = """You are a Threat Intelligence Expert, your task is to provide details threat analysis on user provided CVE.
Follow this below guidelines before giving the answer.
Guidelines:
1. Check if you have relevant user preferences or history from previous conversations
2. Always Use the fetch_cve tool to fetch all the details regaring CVE and fetch_rag tool to provide full threatmodel along with correct mermaid syntax.
3. By using the get_all tool you will get a json output, you need to give all the information verbaly along with mermaid code present in the json.
5. Always provide a clear, concise answer based on the retrieved information
6. If you cannot find relevant information, clearly state that
"""

# Create the agent with memory configurations
agent = create_agent(
    model=llm,
    tools=tools,
    checkpointer=checkpointer,
    store=store,
    middleware=[MemoryMiddleware()],
    system_prompt=system_prompt,
)

@agentcore_app.entrypoint
def agent_invocation(payload, context):
    """Handler for agent invocation in AgentCore runtime with memory support"""
    print("Received payload:", payload)
    print("Context:", context)
    
    # Extract query from payload
    query = payload.get("prompt", "No prompt found in input")
    
    # Extract or generate actor_id and thread_id
    actor_id = payload.get("actor_id", "default-user")
    thread_id = payload.get("thread_id", payload.get("session_id", "default-session"))
    
    # Configure memory context
    config = {
        "configurable": {
            "thread_id": thread_id,  # Maps to AgentCore session_id
            "actor_id": actor_id     # Maps to AgentCore actor_id
        }
    }
    
    # Invoke the agent with memory
    result = agent.invoke(
        {"messages": [("human", query)]},
        config=config
    )
    
    
    # Extract the final answer from the result
    messages = result.get("messages", [])
    answer = messages[-1].content if messages else "No response generated"
    
    # Return the answer
    return {
        "result": answer,
        "actor_id": actor_id,
        "thread_id": thread_id
    }


if __name__ == "__main__":
    agentcore_app.run()