"""RAG 파이프라인: 공정 SOP 문서를 청킹→임베딩→인메모리 벡터스토어 인덱싱→검색.

InMemoryVectorStore를 사용해 네이티브 의존성(FAISS/Chroma) 없이 어디서나 동작한다.
운영 단계에서는 pgvector/Milvus 등으로 교체 가능하도록 retriever 인터페이스만 노출한다.
"""
from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.config import DATA_DIR, EMBEDDING_MODEL


def _load_and_split() -> list[Document]:
    """SOP 마크다운을 섹션(헤더) 단위 + 길이 기준으로 청킹한다.

    제조 SOP는 '공정코드 단위' 의미 경계가 중요하므로 헤더 기준 분할을 1차로 적용한다.
    """
    text = (DATA_DIR / "process_sop.md").read_text(encoding="utf-8")

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "section")]
    )
    sections = header_splitter.split_text(text)

    # 섹션이 너무 길면 추가 분할 (overlap으로 맥락 보존)
    char_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = char_splitter.split_documents(sections)

    # 메타데이터에 섹션명 보존 → 답변 시 출처 인용에 사용
    for c in chunks:
        c.metadata.setdefault("source", "process_sop.md")
    return chunks


@lru_cache(maxsize=1)
def get_retriever(k: int = 3):
    """벡터스토어를 1회 빌드하고 retriever를 캐싱해 반환한다."""
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    store = InMemoryVectorStore(embeddings)
    store.add_documents(_load_and_split())
    return store.as_retriever(search_kwargs={"k": k})


def search_docs(query: str, k: int = 3) -> str:
    """질의에 대해 상위 k개 청크를 검색하고 출처와 함께 문자열로 반환한다."""
    docs = get_retriever(k).invoke(query)
    if not docs:
        return "관련 문서를 찾지 못했습니다."
    parts = []
    for d in docs:
        section = d.metadata.get("section", d.metadata.get("h1", "?"))
        parts.append(f"[출처: {d.metadata.get('source')} / {section}]\n{d.page_content.strip()}")
    return "\n\n---\n\n".join(parts)
