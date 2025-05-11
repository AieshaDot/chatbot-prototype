
import tiktoken

def count_tokens(messages, model="gpt-4"):
    enc = tiktoken.encoding_for_model(model)
    return sum(len(enc.encode(msg["content"])) for msg in messages)

def trim_messages_to_fit_token_limit(messages, max_tokens=8000):
    trimmed = []
    total = 0
    for msg in reversed(messages):
        token_count = len(msg["content"]) // 4  # quick estimate
        if total + token_count > max_tokens:
            break
        trimmed.insert(0, msg)
        total += token_count
    return trimmed

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import openai
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
from vector_store import vectorstore
from fastapi.responses import JSONResponse


# Load environment variables
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# FastAPI app
app = FastAPI()

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

class AskRequest(BaseModel):
    query: str


# Streaming generator for response
async def stream_openai_response(messages):
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=trim_messages_to_fit_token_limit(messages),
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
@app.post("/chat", response_class=StreamingResponse)
async def chat(request: MessageRequest):
    messages = [
        {"role": "system", "content": "You are a helpful assistant named Chereena that answers ITSMF questions. Use line breaks, numbered lists, or bullet points if applicable. Format your responses using markdown-like structure."},
        {"role": "user", "content": request.message}
    ]

    def generate():
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=trim_messages_to_fit_token_limit(messages),
                stream=True
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"⚠️ Server error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")


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

@app.post("/ask")
async def ask_with_rag(request: AskRequest):
    try:
        query = request.query
        context_docs = query_similar_documents(query)

        # ✅ Step 1: Decide whether RAG applies
        if context_docs and any(doc.strip() for doc in context_docs):
            # ✅ Step 2: Add chatbot instructions and RAG context
            prompt = (
                "You are Chereena, a professional, helpful chatbot for ITSMF.\n"
                "Use the following context from internal documents to answer the user's question accurately:\n\n"
                + "\n\n".join(context_docs)
                + f"\n\nUser Question: {query}"
            )
        else:
            # ✅ Step 3: No context found — fallback behavior
            prompt = (
                "You are Chereena, an ITSMF chatbot. "
                "The user's question was not found in your internal knowledge base. "
                "Give a helpful and honest response, or suggest contacting ITSMF directly.\n\n"
                f"User Question: {query}"
            )

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]

        def stream():
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=trim_messages_to_fit_token_limit(messages),
                stream=True
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        return StreamingResponse(stream(), media_type="text/plain")
    except Exception as e:
        return {"error": str(e)}
    
@app.post("/upload-doc")
async def upload_document(file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1].lower()
    contents = await file.read()
    path = f"temp_{file.filename}"

    with open(path, "wb") as f:
        f.write(contents)

    if ext == "pdf":
        text = extract_text_from_pdf(path)
    elif ext == "docx":
        text = extract_text_from_docx(path)
    elif ext == "xlsx":
        text = extract_text_from_xlsx(path)
    else:
        return {"error": "Unsupported file type. Use PDF, DOCX, or XLSX."}

    if not text.strip():
        return {"error": "File was uploaded, but no readable text was extracted."}

    add_documents([text])
    return {"message": f"{file.filename} added to vector store."}
    
    templates = Jinja2Templates(directory="templates")

@app.get("/upload", response_class=HTMLResponse)
async def show_upload(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/vector-docs")
async def get_vector_docs():
    try:
        collection = vectorstore._collection  # Access raw Chroma collection
        results = collection.get()
        return JSONResponse(content=results)
    except Exception as e:
        return {"error": str(e)}