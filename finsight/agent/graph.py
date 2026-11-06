"""LangGraph agent with a free local LLM (Ollama). The graph routes between SQL, RAG and quant tools."""
import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from finsight.agent.tools import TOOLS
from finsight.config import OLLAMA_HOST, OLLAMA_MODEL

SYSTEM_PROMPT = """You are FinSight AI, a financial research copilot for analysts. You explain, you do not give
buy/sell advice and you never predict prices.

STRICT RULES
1. NUMBERS come from tools only. Never invent, estimate or recall a figure from memory.
   - SQL tools (company_overview, financials, price_performance, compare, sector_companies) = what happened.
   - risk_metrics and portfolio = computed math (volatility, Sharpe, drawdown, beta, portfolios).
   - search_filings = why / what the company says (10-K text).
2. For 'why' questions, call BOTH a number tool and search_filings, then connect them.
3. If a tool returns an error or null values, say the data is unavailable. Never fill the gap.
4. Use the ticker symbol (AAPL, JPM...). The universe has 44 US companies; others are out of scope.
5. Final answer: short, structured, cite which figures came from which tool, mention fiscal years and
   periods. Quote 10-K passages only briefly and say they come from the latest 10-K.
6. Add a one-line reminder that this is research support, not investment advice."""


def build_graph():
    llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0).bind_tools(TOOLS)

    def call_model(state: MessagesState):
        return {"messages": [llm.invoke([SystemMessage(SYSTEM_PROMPT)] + state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", call_model)
    g.add_node("tools", ToolNode(TOOLS, handle_tool_errors=True))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")
    return g.compile()


_graph = None


def ask(question: str) -> dict:
    """Run the agent. Returns the answer, the tools used (evidence trail) and latency."""
    global _graph
    _graph = _graph or build_graph()
    t0 = time.time()
    try:
        out = _graph.invoke({"messages": [HumanMessage(question)]}, {"recursion_limit": 14})
    except GraphRecursionError:
        return {"answer": "I could not finish within the allowed number of tool steps. Please narrow the question.",
                "tools_used": [], "latency_ms": int((time.time() - t0) * 1000), "status": "error"}
    msgs = out["messages"]
    tools_used = [m.name for m in msgs if isinstance(m, ToolMessage)]
    answer = next((m.content for m in reversed(msgs) if isinstance(m, AIMessage) and m.content), "")
    return {"answer": answer, "tools_used": tools_used, "latency_ms": int((time.time() - t0) * 1000), "status": "ok"}
