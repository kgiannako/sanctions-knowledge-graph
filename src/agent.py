import os
import json
import datetime
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
# Note: deprecation warning about langchain.agents is misleading —
# langchain is not installed and langgraph.prebuilt is the correct import
from langgraph.prebuilt import create_react_agent
from src.tools import search_entities, graph_lookup, get_consolidated_profile

load_dotenv()

# --- Tool definitions for the agent ---

@tool
def search_sanctions_entities(query: str, entity_type: str = None) -> str:
    """
    Search for sanctioned entities by name using semantic similarity.
    Use this first when you have a name but no entity ID.
    entity_type can be 'Person', 'Organisation', or 'Vessel' — leave empty to search all types.
    Returns a list of matching entities with their IDs and confidence scores.
    """
    results = search_entities(query=query, entity_type=entity_type, top_k=5)
    if not results:
        return "No entities found matching that query."
    return json.dumps(results, indent=2)


@tool
def get_entity_profile(entity_id: str) -> str:
    """
    Get a consolidated profile for a sanctioned entity by ID.
    Merges information from all sanctions lists via SAME_AS links.
    Returns full details including aliases, programs, linked entities, and relationships.
    Use this after search_sanctions_entities to get full details on a specific entity.
    """
    profile = get_consolidated_profile(entity_id)
    if "error" in profile:
        return f"Error: {profile['error']}"
    return json.dumps(profile, indent=2, default=str)


@tool
def get_linked_entities(entity_id: str) -> str:
    """
    Get all entities directly linked to this entity in the knowledge graph.
    Shows SAME_AS cross-source matches and any ownership or association relationships.
    Use this to trace connections between entities for multi-hop reasoning.
    """
    result = graph_lookup(entity_id)
    if "error" in result:
        return f"Error: {result['error']}"

    output = {
        "entity": {
            "id": result["entity"].get("id"),
            "name": result["entity"].get("name"),
            "type": result["entity"].get("type"),
            "source": result["entity"].get("source"),
        },
        "same_as_links": result["same_as"],
        "relationships": result["relationships"],
    }
    return json.dumps(output, indent=2, default=str)


# --- Agent setup ---

def build_agent():
    model = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0,
    )

    tools = [
        search_sanctions_entities,
        get_entity_profile,
        get_linked_entities,
    ]

    agent = create_react_agent(model, tools)
    return agent


# --- Trace logging ---

def log_run(query: str, result: dict, log_path: str = "data/agent_traces.jsonl"):
    os.makedirs("data", exist_ok=True)
    trace = {
        "timestamp": datetime.datetime.now().isoformat(),
        "query": query,
        "messages": [
            {
                "role": m.type,
                "content": m.content if isinstance(m.content, str) else str(m.content)
            }
            for m in result["messages"]
        ]
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(trace) + "\n")


# --- Run agent ---

def run_agent(query: str, verbose: bool = True) -> str:
    agent = build_agent()

    if verbose:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")

    result = agent.invoke({
        "messages": [HumanMessage(content=query)]
    })

    log_run(query, result)

    # extract final answer
    final_message = result["messages"][-1]
    answer = final_message.content

    if verbose:
        print(f"\n--- Agent trace ---")
        for msg in result["messages"]:
            if msg.type == "human":
                print(f"\n[User] {msg.content}")
            elif msg.type == "ai":
                if isinstance(msg.content, list):
                    for block in msg.content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                print(f"\n[Agent] {block['text']}")
                            elif block.get("type") == "tool_use":
                                print(f"\n[Tool call] {block['name']}({json.dumps(block.get('input', {}), indent=2)})")
                else:
                    print(f"\n[Agent] {msg.content}")
            elif msg.type == "tool":
                content = msg.content
                if len(str(content)) > 300:
                    content = str(content)[:300] + "..."
                print(f"\n[Tool result] {content}")

        print(f"\n{'='*60}")
        print(f"Final answer: {answer}")
        print(f"{'='*60}\n")

    return answer


if __name__ == "__main__":
    queries = [
        "What do you know about Bin Laden across all sanctions lists?",
        "Is the vessel EBANO sanctioned and what do we know about it?",
        "Tell me about Al Qaeda and which sanctions programs it appears in.",
    ]

    for query in queries:
        run_agent(query)