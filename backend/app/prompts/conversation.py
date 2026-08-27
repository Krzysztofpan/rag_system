CONVERSATION_METADATA_TEMPLATE = """\
Based on the current title and a new document summary, create a conversation title and select a topic.

Title should be general and short, so the user knows what the conversation is about.
If the document is not related to any of the topics, return topic 'general'.

document summary: {doc_summary}

current_title: {conversation_title}
"""
