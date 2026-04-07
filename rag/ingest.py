import os
from pathlib import Path
from dotenv import load_dotenv

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings
import chromadb

load_dotenv()

DOCS_PATH = Path(__file__).parent.parent / "contractor_docs"
CHROMA_PATH = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "contractor_en"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"


def build_index() -> VectorStoreIndex:
    print(f"Loading docs from: {DOCS_PATH}")

    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
    

    documents = SimpleDirectoryReader(str(DOCS_PATH)).load_data()
    print(f"Loaded {len(documents)} document(s)")

    #splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    splitter = SentenceSplitter(chunk_size=256, chunk_overlap=30)
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"Created {len(nodes)} chunks")

    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex(
        nodes,
        storage_context=storage_context,
    )
    print(f"Index built and saved to: {CHROMA_PATH}")
    return index


def load_index() -> VectorStoreIndex:
    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
    

    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
    )
    print("Index loaded from ChromaDB")
    return index


if __name__ == "__main__":
    build_index()