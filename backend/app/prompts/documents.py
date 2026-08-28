DOCUMENT_SUMMARY_TEMPLATE = """\
Summarize document based on content:

{document_content}
"""

DOCUMENTS_CATALOG_TEMPLATE = """\
Write a short catalog of the documents in this conversation.

Describe what the documents are, what kinds of information they contain,
and whether they relate to each other. This is an index for a reader and
for choosing document search — not a recap of every fact.

Keep it under 180 words. Write in the same language as the document
summaries. You may bold a few key terms with markdown.

Documents:
{document_entries}
"""

DOCUMENTS_CATALOG_ENTRY_CHAR_LIMIT = 800
