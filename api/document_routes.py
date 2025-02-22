from fastapi import APIRouter
from services.document_service import DocumentService

router = APIRouter(prefix="/api/documents", tags=["Documents"])
document_service = DocumentService()

@router.post("/index")
async def index_document(document_id: str, content: str, metadata: dict):
    return document_service.index_document(document_id, content, metadata)

@router.get("/search")
async def search_documents(query: str):
    return document_service.search_documents(query)