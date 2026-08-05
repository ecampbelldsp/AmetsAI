from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

class State(TypedDict):
    messages: Annotated[list, add_messages]

def manage_context_window(messages: list, max_recent_messages: int = 1):
    """
    Prevents VRAM overflow by keeping only the System Prompt + the latest N messages.
    max_recent_messages = 6 means keeping the last 3 user/AI conversational turns.
    """
    if len(messages) <= max_recent_messages + 1:
        return messages

    # Extract the system prompt (always the first message)
    system_prompt = messages[0]
    # Extract the most recent conversation history
    recent_history = messages[-max_recent_messages:]

    # Recombine them into a safe payload for the 2048 token limit
    return [system_prompt] + recent_history

def create_agent(
    model_name: str = "Qwen/Qwen2.5-3B-Instruct-AWQ",
    api_base: str = "http://localhost:8000/v1",
    temperature: float = 0.1
):
    llm = ChatOpenAI(
        model_name=model_name,
        base_url=api_base,
        api_key="EMPTY",
        temperature=temperature,
        streaming=True
    )

    def chatbot_node(state: State):
        """Prunes the state, passes it to the LLM, and returns the response."""
        safe_messages = manage_context_window(state["messages"])
        response = llm.invoke(safe_messages)
        return {"messages": [response]}

    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)

    memory = MemorySaver()
    agent_app = graph_builder.compile(checkpointer=memory)
    
    return agent_app