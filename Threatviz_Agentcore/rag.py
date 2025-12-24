import os
import json
import tempfile
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader, JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Paths and files
INDEX_PATH = "my_rag_db"
PDF_FILE = "threat_models.pdf"
URLS = [
    "https://mermaid.js.org/intro/syntax-reference.html",
    "https://mermaid.js.org/syntax/sequenceDiagram.html",
    "https://mermaid.js.org/syntax/classDiagram.html",
    "https://mermaid.js.org/syntax/stateDiagram.html",
    "https://mermaid.js.org/syntax/entityRelationshipDiagram.html",
    "https://mermaid.js.org/syntax/pie.html",
    "https://mermaid.js.org/syntax/c4.html",
    "https://mermaid.js.org/syntax/architecture.html"
]

def load_documents(pdf_file=None, urls=None, json_dict=None):
    """
    Load documents from PDF, URLs, or JSON dict.
    Returns a list of LangChain Document objects.
    """
    docs = []

    # Load PDF
    if pdf_file and os.path.exists(pdf_file):
        docs += PyPDFLoader(pdf_file).load()

    # Load URLs
    if urls:
        for url in urls:
            docs += WebBaseLoader(url).load()

    # Load JSON dict
    if json_dict:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump(json_dict, f)
            f.flush()
            loader = JSONLoader(
                file_path=f.name,
                jq_schema=".users[]",  # adjust as needed
                text_content=False
            )
            docs += loader.load()

    if not docs:
        raise ValueError("No documents loaded. Please check inputs.")

    return docs

def build_vectorstore(documents, index_path=INDEX_PATH):
    """
    Split documents into chunks, embed them, and save FAISS vectorstore locally.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(index_path)
    return vectorstore

def load_vectorstore(index_path=INDEX_PATH):
    """
    Load FAISS vectorstore from disk.
    """
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)

def retrieve_framework_context(query: str, k: int = 5) -> str:
    """
    Retrieve the top-k most relevant chunks from the vectorstore for a query.
    """
    if os.path.exists(INDEX_PATH):
        vectorstore = load_vectorstore()
    else:
        docs = load_documents(pdf_file=PDF_FILE, urls=URLS)
        vectorstore = build_vectorstore(docs)

    results = vectorstore.similarity_search(query, k=k)
    return "\n\n".join([d.page_content for d in results])
