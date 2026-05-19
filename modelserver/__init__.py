# The `modelserver` compose service: a separate FastAPI inference server for
# the classifier, NER, and summarizer. The chatbot reaches these over HTTP
# (never imported in-process). Kept separate so the api image stays lean.
