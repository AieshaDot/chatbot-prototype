from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import CharacterTextSplitter
from chromadb import PersistentClient

chroma_client = PersistentClient(path="chroma_db")
embedding_model = OpenAIEmbeddings()

vectorstore = Chroma(
    client=chroma_client,
    collection_name="itsmf_knowledge",
    embedding_function=embedding_model
)

text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)

def add_documents(texts: list[str]):
    chunks = text_splitter.create_documents(texts)
    content = [chunk.page_content for chunk in chunks]
    vectorstore.add_texts(texts=content)

def query_similar_documents(query: str, k: int = 4):
    docs = vectorstore.similarity_search(query, k=k)
    return [doc.page_content for doc in docs]