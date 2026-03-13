"""
Celery task: index_document_task
  1. Load file from disk
  2. Extract text
  3. Semantic chunk
  4. Embed + update FAISS
  5. Write chunks to DB
  6. Update document.status = 'ready'
"""
from celery_app import celery_app


@celery_app.task(
    name="tasks.indexing.index_document_task",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def index_document_task(self, document_id: str):
    """Celery task for asynchronous document indexing."""
    import asyncio

    async def _run():
        from core.database import AsyncSessionLocal
        from core.models import Document
        from services.chunking import chunk_and_index_document
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalar_one_or_none()
            if not doc:
                return

            doc.status = "indexing"
            await db.commit()

            try:
                await chunk_and_index_document(doc, db)
                doc.status = "ready"
            except Exception as exc:
                doc.status = "failed"
                await db.commit()
                raise self.retry(exc=exc)

            await db.commit()

    asyncio.run(_run())
