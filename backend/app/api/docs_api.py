"""Documentation API — serves markdown docs as rendered content."""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/api/docs", tags=["Documentation"])

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs")
# Also check /app/docs in Docker
DOCS_DIRS = [DOCS_DIR, "/app/docs", "docs"]

ALLOWED_FILES = [
    "SECURITY.md", "COMPLIANCE_MAPPING.md", "TENANT_SECURITY.md",
    "ARCHITECTURE.md", "API_REFERENCE.md", "AZURE_DEPLOYMENT.md",
    "ONBOARDING.md",
]


def find_doc(filename: str) -> str | None:
    for d in DOCS_DIRS:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            return path
    return None


@router.get("/list")
async def list_docs():
    """List available documentation files."""
    docs = []
    for f in ALLOWED_FILES:
        path = find_doc(f)
        if path:
            size = os.path.getsize(path)
            docs.append({"file": f, "size_bytes": size, "available": True})
        else:
            docs.append({"file": f, "available": False})
    return {"docs": docs}


@router.get("/{filename}")
async def get_doc(filename: str):
    """Get a documentation file as raw markdown."""
    if filename not in ALLOWED_FILES:
        raise HTTPException(status_code=404, detail=f"Document not found: {filename}")

    path = find_doc(filename)
    if not path:
        raise HTTPException(status_code=404, detail=f"Document file not found on server")

    with open(path, "r") as f:
        content = f.read()

    return {
        "file": filename,
        "content": content,
        "size_bytes": len(content),
    }
