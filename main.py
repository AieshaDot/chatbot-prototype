import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import openai
from openai import OpenAI
from dotenv import load_dotenv
import asyncio
import markdown2
from vector_store import add_documents, query_similar_documents
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi import UploadFile, File
from load_docs import extract_text_from_pdf, extract_text_from_docx, extract_text_from_xlsx
from vector_store import add_documents
from fastapi import UploadFile, File
from vector_store import add_documents, query_similar_documents
from fastapi.responses import JSONResponse
import tiktoken
from pathlib import Path
from load_docs import (extract_text_from_pdf, extract_text_from_docx, extract_text_from_xlsx, extract_text_from_txt)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from vector_store import retriever, add_documents, query_similar_documents
from fastapi import Request
from fastapi.responses import StreamingResponse, JSONResponse
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import asyncio
from vector_store import retriever
import nltk



# Load environment variables
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# FastAPI app
app = FastAPI()

# Load ITSMF system instructions
itsmf_prompt = Path("itsmf_instructions.txt").read_text().strip()


# 🔧 Truncation helper function
def truncate_messages(messages, max_tokens=6000):
    truncated = []
    total_tokens = 0
    for message in reversed(messages):
        token_estimate = len(message['content']) // 4  # ≈ 4 chars per token
        if total_tokens + token_estimate <= max_tokens:
            truncated.insert(0, message)
            total_tokens += token_estimate
        else:
            break
    return truncated



# Mount static directory for CSS, JS, and images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates directory
templates = Jinja2Templates(directory="templates")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class MessageRequest(BaseModel):
    message: str

class AddDocsRequest(BaseModel):
    texts: list[str]

# class AskRequest(BaseModel):
#     query: str

class AskRequest(BaseModel):
    message: str


def count_tokens(messages, model="gpt-4"):
    enc = tiktoken.encoding_for_model(model)
    return sum(len(enc.encode(msg["content"])) for msg in messages)

def trim_messages_to_fit_token_limit(messages, max_tokens=8000, model="gpt-4"):
    enc = tiktoken.encoding_for_model(model)
    total_tokens = 0
    trimmed = []

    for msg in reversed(messages):
        token_count = len(enc.encode(msg.get("content", ""))) + 4  # +4 for role/structure
        if total_tokens + token_count > max_tokens:
            break
        trimmed.insert(0, msg)
        total_tokens += token_count

    if not trimmed:
        # fallback to last user message and system prompt
        return [messages[0], messages[-1]]

    return trimmed


# Streaming generator for response
async def stream_openai_response(messages):
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            # messages=trim_messages_to_fit_token_limit(messages),
            messages = truncate_messages(messages, max_tokens=6000),
            stream=True
        )
        async def generate():
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    delta = chunk.choices[0].delta.content
                    if delta:
                        html_chunk = markdown2.markdown(delta)
                        # Remove newlines so SSE formatting isn't broken
                        cleaned = html_chunk.replace("\n", "")
                        yield f"data: {cleaned}\n\n"
                    await asyncio.sleep(0.01)
        return generate()
    except Exception as e:
        async def error_gen():
            yield f"Error: {str(e)}"
        return error_gen()

# Chat endpoint (streaming)
from fastapi.responses import StreamingResponse



# New Chat Window
@app.get("/new_chat", response_class=HTMLResponse)
async def serve_new_chat(request: Request):
    return templates.TemplateResponse("new_chat.html", {"request": request})

# Serve the chatbot homepage
@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("C_LM_Home.html", {"request": request})

# ✅ Route for privacy policy
@app.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    return templates.TemplateResponse("privacy_policy.html", {"request": request})

# Routes
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("C_LM_Home.html", {"request": request})


@app.post("/add-docs")
async def add_docs(request: AddDocsRequest):
    try:
        add_documents(request.texts)
        return {"message": "Documents added successfully"}
    except Exception as e:
        return {"error": str(e)}



# 🔐 Load .env values
load_dotenv()

# ✅ Instantiate new OpenAI client (no API key needed in code)
client = OpenAI()

@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    query = data.get("message", "")
    if not query:
        return JSONResponse({"error": "Missing 'message' field"}, status_code=400)

    try:
        system_prompt = Path("itsmf_instructions.txt").read_text().strip()
        docs = retriever.get_relevant_documents(query)
        context = "\n\n".join(doc.page_content for doc in docs)
        for doc in docs:
            print(f"📄 Source: {doc.metadata.get('source', '❌ no source')}, Content: {doc.page_content[:100]}")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{query}\n\nUse this ITSMF context:\n{context}"}
        ]

    except Exception as e:
        print("❌ Setup Error:", e)
        return JSONResponse({"error": str(e)}, status_code=500)

    async def stream_openai():
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                stream=True
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                await asyncio.sleep(0)
        except Exception as e:
            print("❌ Stream Error:", e)
            yield f"[ERROR]: {str(e)}"

    return StreamingResponse(stream_openai(), media_type="text/plain")
    

from fastapi import UploadFile, File
import os
import shutil
from vector_store import add_documents

from load_docs import load_and_index_file  # ✅ Make sure this is at the top

@app.post("/upload-doc")
async def upload_doc(file: UploadFile = File(...)):
    file_location = f"uploaded_files/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())

    # ✅ Embed the uploaded file into Chroma vector store
    try:
        chunk_count = load_and_index_file(file_location)
        return {"message": f"✅ Uploaded and added {chunk_count} chunks from {file.filename}"}
    except Exception as e:
        import traceback
        print("🔥 Upload failed:", traceback.format_exc())
        return {"error": str(e)}


@app.get("/upload", response_class=HTMLResponse)
async def show_upload(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

from vector_store import vectordb
from fastapi.responses import JSONResponse

@app.get("/vector-docs")
async def list_vector_documents():
    try:
        # Pull all stored docs
        results = vectordb.get(include=["documents", "metadatas"])

        # Safely slice to first 100 if too many
        docs = results.get("documents", [])[:100]
        metas = results.get("metadatas", [])[:100]

        # Combine into structured list
        combined = []
        for doc, meta in zip(docs, metas):
            combined.append({
                "text": doc,
                "metadata": meta
            })

        return {"documents": combined}

    except Exception as e:
        print("❌ Error fetching vector docs:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@app.get("/vector-filenames")
async def list_uploaded_filenames():
    try:
        results = vectordb.get(include=["metadatas"])
        metas = results.get("metadatas", [])[:200]  # adjust limit if needed

        # Extract just 'source' fields (filenames)
        filenames = [meta.get("source") for meta in metas if "source" in meta]

        # Optionally remove duplicates and nulls
        unique_filenames = sorted(set(f for f in filenames if f))

        return {"filenames": unique_filenames}

    except Exception as e:
        print("❌ Error fetching filenames:", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
    

from fastapi.responses import JSONResponse

@app.get("/list-docs")
def list_documents():
    try:
        from vector_store import get_vectorstore
        vs = get_vectorstore()
        all_docs = vs._collection.get(include=["metadatas", "documents"])
        return {"documents": all_docs}
    except Exception as e:
        import traceback
        print("🔥 Error in /list-docs:", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


from pydantic import BaseModel
from typing import List

class DeleteRequest(BaseModel):
    sources: List[str]

@app.post("/delete-docs")
def delete_documents(payload: DeleteRequest):
    from vector_store import get_vectorstore
    vs = get_vectorstore()

    collection = vs._collection.get(include=["metadatas"])
    all_ids = vs._collection.get()["ids"]  # ✅ fix here

    ids_to_delete = [
        all_ids[i]
        for i, meta in enumerate(collection["metadatas"])
        if meta.get("source") in payload.sources
    ]

    vs._collection.delete(ids=ids_to_delete)
    return {"deleted_count": len(ids_to_delete)}

@app.get("/manage-docs", response_class=HTMLResponse)
def manage_docs(request: Request):
    return templates.TemplateResponse("manage_docs.html", {"request": request})

@app.post("/purge-vector-db")
def purge_vector_db():
    from vector_store import get_vectorstore
    vs = get_vectorstore()
    vs._collection.delete(where={"source": {"$ne": ""}})
    return {"message": "✅ Vector database purged."}
