"""Conversation + message persistence. SQL only.

Backs the chat history. Deletion of a conversation must produce an audit-log
row — that orchestration is the service's job, not this repo's.
"""

# TODO: create_conversation, append_message, list_for_user, delete
