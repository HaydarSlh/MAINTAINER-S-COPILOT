# RAG offline indexing pipeline (build-time, not a runtime container).
# Corpus = project docs + held-out resolved issues with maintainer answers.
# Produces the pgvector index the api's rag_service queries at runtime.
