try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    print("pysqlite3-binary not found, using sqlite3 instead.")


import os
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores.chroma import Chroma
from evo_researcher.models.WebScrapeResult import WebScrapeResult
from langchain.text_splitter import RecursiveCharacterTextSplitter


def create_embeddings_from_results(results: list[WebScrapeResult], text_splitter: RecursiveCharacterTextSplitter, api_key: str | None = None) -> Chroma:
    if api_key == None:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    
    collection = Chroma(embedding_function=OpenAIEmbeddings(api_key=api_key))
    texts = []
    metadatas = []

    for scrape_result in results:
        text_splits = text_splitter.split_text(scrape_result.content)
        texts += text_splits
        metadatas += [scrape_result.dict() for _ in text_splits]

    collection.add_texts(
        texts=texts,
        metadatas=metadatas
    )
    return collection
