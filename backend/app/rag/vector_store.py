import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from app.config import settings
from typing import List, Dict, Any
import os

os.makedirs(settings.chroma_persist_dir, exist_ok=True)

_embeddings = None
_vectorstore = None


def get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            openai_api_key=settings.openai_api_key,
            model="text-embedding-3-small"
        )
    return _embeddings


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            collection_name="knowledge_base",
            embedding_function=get_embeddings(),
            persist_directory=settings.chroma_persist_dir,
        )
    return _vectorstore


def add_documents(texts: List[str], metadatas: List[dict], doc_id: int) -> int:
    vs = get_vectorstore()
    ids = [f"doc_{doc_id}_chunk_{i}" for i in range(len(texts))]
    vs.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    return len(texts)


def delete_document(doc_id: int):
    vs = get_vectorstore()
    collection = vs._collection
    results = collection.get(where={"document_id": doc_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])


def similarity_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    vs = get_vectorstore()
    results = vs.similarity_search_with_relevance_scores(query, k=k)
    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score),
        }
        for doc, score in results
        if float(score) > 0.3
    ]
