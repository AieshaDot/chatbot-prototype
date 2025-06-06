# debug_vectordb.py

from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings

PERSIST_DIR = "chroma_db"  # Change if your DB is in a different folder

vs = Chroma(persist_directory=PERSIST_DIR, embedding_function=OpenAIEmbeddings())

print("\n🔍 Loading vector store contents...\n")
collection = vs._collection.get(include=["documents", "metadatas"])

print(f"Total chunks found: {len(collection['documents'])}\n")

# Preview some metadata entries
for i, meta in enumerate(collection["metadatas"][:10]):
    print(f"{i+1:>2}) Source: {meta.get('source', '❌ No source')}")