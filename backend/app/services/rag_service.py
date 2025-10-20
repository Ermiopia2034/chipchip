import os
import logging
from typing import List, Optional

import chromadb
from chromadb.utils import embedding_functions
import requests

try:
    # Prefer explicit import for HTTP client when available
    from chromadb import HttpClient as ChromaHttpClient
except Exception:  # pragma: no cover - fallback for older versions
    ChromaHttpClient = None

import google.generativeai as genai

from app.config import settings


class VectorDBService:
    """
    Chroma client wrapper for RAG operations.

    Uses HTTP client to connect to the Chroma server defined in docker-compose.
    Embeddings are computed client-side via Google Generative AI embeddings
    using the GEMINI API key.
    """

    def __init__(self,
                 host: str | None = None,
                 port: int | None = None,
                 api_key: Optional[str] = None):
        self._host = host or settings.CHROMA_HOST
        self._port = port or settings.CHROMA_PORT
        self._api_key = api_key if api_key is not None else (os.getenv("GOOGLE_API_KEY") or settings.GEMINI_API_KEY)

        if ChromaHttpClient is None:
            raise RuntimeError("Chroma HTTP client not available in this chromadb version.")

        # Force REST path for AI Studio API key usage
        os.environ.setdefault("GOOGLE_GENAI_USE_GRPC", "false")
        if self._api_key:
            genai.configure(api_key=self._api_key)
        else:
            logging.warning("GEMINI/GOOGLE API key not set; embeddings will not work.")

        # Lazy init: do not connect on import. Connect on first use.
        self.client = None
        self.collection = None

    def _ensure_client(self):
        if self.client and self.collection:
            return
        last_err: Exception | None = None
        for attempt in range(1, 11):  # up to ~5s with backoff
            try:
                self.client = ChromaHttpClient(host=self._host, port=self._port)
                # Do NOT attach an embedding_function to avoid server-side embedding (which may use gRPC)
                self.collection = self.client.get_or_create_collection(
                    name="product_knowledge",
                    embedding_function=None,
                    metadata={"hnsw:space": "cosine"},
                )
                return
            except Exception as e:
                last_err = e
                delay = min(0.5 * attempt, 2.0)
                logging.getLogger(__name__).warning(
                    "Chroma not reachable (%s:%s), retry %d/10 in %.1fs: %s",
                    self._host,
                    self._port,
                    attempt,
                    delay,
                    e,
                )
                import time
                time.sleep(delay)
        # Exhausted retries
        raise RuntimeError(f"Could not connect to Chroma at {self._host}:{self._port}: {last_err}")

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Compute embeddings using AI Studio REST API to ensure API key support.
        """
        api_key = os.getenv("GOOGLE_API_KEY") or settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY/GEMINI_API_KEY not set for embeddings")

        # Use AI Studio REST v1 endpoint with API key header
        url = "https://generativelanguage.googleapis.com/v1/models/text-embedding-004:embedContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        vectors: List[List[float]] = []
        for t in texts:
            payload = {
                "model": "models/text-embedding-004",
                "content": {"parts": [{"text": str(t)}]},
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code != 200:
                raise RuntimeError(f"Embedding HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            emb = data.get("embedding") or {}
            values = emb.get("values")
            if not values:
                raise RuntimeError("Embedding response missing values")
            vectors.append(values)
        return vectors

    def ingest_knowledge_base(self, csv_path: str) -> int:
        import pandas as pd

        if not os.path.isfile(csv_path):
            raise FileNotFoundError(f"Knowledge base CSV not found: {csv_path}")

        self._ensure_client()
        df = pd.read_csv(csv_path)
        required_cols = {"embedding_text", "product_name", "category"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"KB CSV missing columns: {missing}")

        documents = df["embedding_text"].astype(str).tolist()
        metadatas = df[["product_name", "category"]].to_dict("records")
        ids = [f"kb_{i}" for i in range(len(df))]

        # Upsert behavior: delete existing IDs first to avoid duplication
        try:
            existing = self.collection.get(ids=ids)
            if existing and existing.get("ids"):
                self.collection.delete(ids=existing["ids"])  # type: ignore
        except Exception:
            pass

        # Compute embeddings client-side to avoid server-side gRPC
        embeddings = self._embed_texts(documents)
        self.collection.add(documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings)
        return len(ids)

    def semantic_search(self, query: str, n_results: int = 3, category: str | None = None) -> dict:
        self._ensure_client()
        where = {"category": category} if category else None
        n = n_results or settings.RAG_TOP_K
        # Client-side embed to avoid server embedding
        emb = self._embed_texts([query])[0]
        result = self.collection.query(query_embeddings=[emb], n_results=n, where=where)  # type: ignore
        return result

    async def async_semantic_search(self, query: str, n_results: int | None = None, category: str | None = None) -> dict:
        # Simple thread offload for compatibility with async call sites
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.semantic_search(query, n_results or settings.RAG_TOP_K, category)
        )
