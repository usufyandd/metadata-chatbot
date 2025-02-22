from openai import OpenAI
from core.elasticsearch_client import es_client
from fastapi import HTTPException
from settings import settings

client = OpenAI(api_key=settings.openai_api_key)

class DocumentService:
    def __init__(self):
        self.es_client = es_client

    def generate_embedding(self, text: str):
        """Generates an OpenAI embedding for a given text."""
        response = client.embeddings.create(model="text-embedding-ada-002", input=text)
        return response["data"][0]["embedding"]

    def index_document(self, document_id: str, content: str, metadata: dict):
        try:
            embedding = self.generate_embedding(content)
            self.es_client.index_document(document_id, content, metadata, embedding)
            return {"message": "Document indexed successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

    def search_documents(self, query: str):
        try:
            query_embedding = self.generate_embedding(query)
            results = self.es_client.search_documents(query_embedding)
            return [hit["_source"] for hit in results]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
