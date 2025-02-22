from elasticsearch import Elasticsearch
from settings import settings

class ElasticsearchClient:
    def __init__(self):
        self.client = Elasticsearch(
            hosts=[{"host": settings.elasticsearch_host, "port": settings.elasticsearch_port, "scheme": "http"}]
        )
        self.index = settings.elasticsearch_index

    def index_document(self, document_id: str, content: str, metadata: dict):
        """Indexes a document with text content and metadata."""
        body = {
            "content": content,
            "metadata": metadata,
        }
        self.client.index(index=self.index, id=document_id, body=body)

    def search_documents(self, query: str):
        """Performs a full-text search on documents."""
        body = {
            "query": {
                "match": {
                    "content": query
                }
            }
        }
        response = self.client.search(index=self.index, body=body)
        return response["hits"]["hits"]

es_client = ElasticsearchClient()
