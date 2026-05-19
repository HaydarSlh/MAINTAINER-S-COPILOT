# The `chatbot` compose service: the Streamlit INTERNAL tool (login, full
# chat, memory inspector, admin widget config). It is NOT the production
# surface — that's the React widget. Both call the same FastAPI backend; this
# app never talks to the DB/Redis directly, only the api over HTTP.
