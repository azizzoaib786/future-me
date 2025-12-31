#!/usr/bin/env python3
# app.py — Future-Me (all GitHub repos, max commits global) using Redis + LangChain + Groq

import os
import uuid
from typing import Optional, Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from github import Github, GithubException

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Redis as RedisVectorStore

from langchain_groq import ChatGroq

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

# ENV configs
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Global max commits across ALL repos
MAX_COMMITS = int(os.getenv("GITHUB_MAX_COMMITS", "100"))

FUTURE_ME_NAME = os.getenv("FUTURE_ME_NAME", "Aziz")
FUTURE_ME_YEARS_AHEAD = int(os.getenv("FUTURE_ME_YEARS_AHEAD", "1"))

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_INDEX_NAME = os.getenv("REDIS_INDEX_NAME", "future_me_github")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is required (Groq Llama 3 key)")
if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN is required")

# GitHub → LangChain Documents (ALL repos, capped globally)
def fetch_all_repos_commits(token: str, max_global_commits: int = 100) -> List[Document]:
    """
    Fetch commits across ALL repos for the authenticated user,
    but stop after max_global_commits commits total (global cap).
    """
    gh = Github(token)
    user = gh.get_user()

    all_docs: List[Document] = []
    total_commits_collected = 0

    print("[init] Fetching list of all repos for user:", user.login)
    repos = list(user.get_repos())
    print(f"[init] Found {len(repos)} repos.")

    # Sort repos by recently updated so we capture current work first
    repos.sort(key=lambda r: r.updated_at, reverse=True)

    for repo in repos:
        if total_commits_collected >= max_global_commits:
            break

        print(f"[init] Fetching commits for repo: {repo.full_name}")

        try:
            commits = repo.get_commits()

            for c in commits:
                if total_commits_collected >= max_global_commits:
                    break

                msg = c.commit.message or ""
                msg = msg.strip()
                if not msg:
                    continue

                author_name = c.commit.author.name if c.commit.author else "Unknown"
                author_email = c.commit.author.email if c.commit.author else ""
                date = c.commit.author.date.isoformat() if c.commit.author else None

                metadata = {
                    "source": "github",
                    "repo": repo.full_name,
                    "sha": c.sha,
                    "author_name": author_name,
                    "author_email": author_email,
                    "date": date,
                    "url": c.html_url,
                }

                all_docs.append(Document(page_content=msg, metadata=metadata))
                total_commits_collected += 1

        except GithubException as e:
            # Handles "Git Repository is empty." and similar errors
            print(f"[init] Skipping repo {repo.full_name} due to error: {e}")
            continue

    print(f"[init] Total commits collected across all repos: {total_commits_collected}")
    return all_docs

# Vector store: Redis (Redis Stack) + retriever
# Using local HuggingFace embeddings → no external embedding API required
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def build_or_refresh_index() -> RedisVectorStore:
    """
    Build a Redis index from commits across all repos.

    For demo:
    - Drops any existing index (so you always rebuild clean).
    In a real system you'd separate ingestion into its own job.
    """
    print(f"[init] Collecting up to {MAX_COMMITS} commits across ALL repos...")
    docs = fetch_all_repos_commits(GITHUB_TOKEN, max_global_commits=MAX_COMMITS)

    print(f"[init] Prepared {len(docs)} commit documents for indexing.")

    # Drop existing index (optional but useful while iterating)
    try:
        RedisVectorStore.drop_index(
            index_name=REDIS_INDEX_NAME,
            delete_documents=True,
            redis_url=REDIS_URL,
        )
        print(f"[init] Dropped existing Redis index '{REDIS_INDEX_NAME}'.")
    except Exception as e:
        print(f"[init] No existing index to drop or drop failed: {e}")

    vs = RedisVectorStore.from_documents(
        documents=docs,
        embedding=embeddings,
        redis_url=REDIS_URL,
        index_name=REDIS_INDEX_NAME,
        vector_schema={"algorithm": "HNSW"},
    )

    print(f"[init] Created Redis index '{REDIS_INDEX_NAME}' with {len(docs)} docs.")
    return vs


vector_store = build_or_refresh_index()
retriever = vector_store.as_retriever(search_kwargs={"k": 8})

# LLM + Prompt (new-style LangChain)
# (Use whichever Groq model is working)
llm = ChatGroq(
    model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),  # or whichever you've set
    temperature=0.7,
)

system_prompt = f"""
You are a simulated FUTURE VERSION of {FUTURE_ME_NAME}, exactly {FUTURE_ME_YEARS_AHEAD} year(s) from now.

You only know what is in the provided context, which is built from their GitHub commit history across ALL their repos:
- commit messages
- repositories
- dates
- authorship patterns

Your job is to:
- Infer realistic future work, skills, and habits of {FUTURE_ME_NAME} based on this history.
- Speak in the first person ("I") as if you are {FUTURE_ME_NAME} in the future.
- Be realistically optimistic, not sci-fi. Do not claim superhuman abilities.
- Use specific references from the context when helpful (repos, commit patterns, technologies).
- Maintain continuity with the ongoing conversation when that helps.
- If the user asks something unrelated to work/coding, you can still respond, but ground your answer in the style/patterns you see.

ALWAYS preface your answer with: "Future-{FUTURE_ME_NAME}:".
""".strip()

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        (
            "system",
            "Here are some relevant snippets from my past GitHub activity:\n{context}",
        ),
        ("human", "{input}"),
    ]
)


def format_context(docs: List[Document]) -> str:
    """Turn retrieved docs into a readable context string."""
    chunks = []
    for d in docs:
        repo = d.metadata.get("repo", "unknown-repo")
        date = d.metadata.get("date", "")
        sha = d.metadata.get("sha", "")[:7]
        prefix = f"[{repo} @ {date} {sha}]".strip()
        chunks.append(f"{prefix}\n{d.page_content}")
    return "\n\n".join(chunks)


# Session history (manual, simple, robust)
_session_store: Dict[str, ChatMessageHistory] = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in _session_store:
        _session_store[session_id] = ChatMessageHistory()
    return _session_store[session_id]

# FastAPI app
app = FastAPI(title="Future-Me Simulator (All GitHub Repos + Redis + Groq)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # 1) Work out session id
    session_id = req.session_id or str(uuid.uuid4())

    # 2) Get (or create) the chat history for this session
    history = get_session_history(session_id)

    # 3) RAG step: retrieve docs based on the user's message
    docs = retriever.invoke(req.message)
    context_str = format_context(docs)

    # 4) Build the full prompt with context + history
    prompt_messages = prompt.format_prompt(
        input=req.message,
        chat_history=history.messages,
        context=context_str,
    ).to_messages()

    # 5) Call the LLM
    response = llm.invoke(prompt_messages)
    answer = response.content

    # 6) Update history with this new turn
    history.add_user_message(req.message)
    history.add_ai_message(answer)

    # 7) Return reply + session id to the frontend
    return ChatResponse(reply=answer, session_id=session_id)


# Serve static files (chat UI) — MUST be last so /api/chat is not shadowed
app.mount("/", StaticFiles(directory="static", html=True), name="static")