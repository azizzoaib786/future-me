#!/usr/bin/env python3
# app.py — Future-Me (all GitHub repos, max commits global) using Redis + LangChain + OpenAI

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
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Redis as RedisVectorStore
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory

# Env & config
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN   = os.getenv("GITHUB_TOKEN")

# Global max commits across ALL repos
MAX_COMMITS    = int(os.getenv("GITHUB_MAX_COMMITS", "100"))

FUTURE_ME_NAME        = os.getenv("FUTURE_ME_NAME", "Aziz")
FUTURE_ME_YEARS_AHEAD = int(os.getenv("FUTURE_ME_YEARS_AHEAD", "1"))

REDIS_URL        = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_INDEX_NAME = os.getenv("REDIS_INDEX_NAME", "future_me_github")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is required")
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

            # Important: wrap the iteration itself in try/except
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
            # This catches "Git Repository is empty." and any similar API errors
            print(f"[init] Skipping repo {repo.full_name} due to error: {e}")
            continue

    print(f"[init] Total commits collected across all repos: {total_commits_collected}")
    return all_docs

# Vector store: Redis (Redis Stack / RedisVL) + retriever
embeddings = OpenAIEmbeddings()

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
        # HNSW is generally a good choice for approximate nearest neighbour
        vector_schema={"algorithm": "HNSW"},
    )

    print(f"[init] Created Redis index '{REDIS_INDEX_NAME}' with {len(docs)} docs.")
    return vs

vector_store = build_or_refresh_index()
retriever = vector_store.as_retriever(search_kwargs={"k": 8})

# LangChain QA chain with chat history
def build_base_chain():
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)

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
            ("human", "{input}"),
        ]
    )

    doc_chain = create_stuff_documents_chain(llm, prompt)
    retrieval_chain = create_retrieval_chain(retriever, doc_chain)
    return retrieval_chain

base_chain = build_base_chain()

# In-memory session → chat history mapping
_session_store: Dict[str, ChatMessageHistory] = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in _session_store:
        _session_store[session_id] = ChatMessageHistory()
    return _session_store[session_id]

chain_with_history = RunnableWithMessageHistory(
    base_chain,
    lambda config: get_session_history(config["configurable"]["session_id"]),
    input_messages_key="input",
    history_messages_key="chat_history",
)

# FastAPI app
app = FastAPI(title="Future-Me Simulator (All GitHub Repos + RedisVL)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (chat UI)
app.mount("/", StaticFiles(directory="static", html=True), name="static")


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    result = chain_with_history.invoke(
        {"input": req.message},
        config={"configurable": {"session_id": session_id}},
    )

    reply = result["answer"]
    return ChatResponse(reply=reply, session_id=session_id)