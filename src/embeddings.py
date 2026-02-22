from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
from openai import OpenAI

from src.config import get_openai_api_key

try:  # FAISS 설치 여부는 실제 사용 시점에 확인
    import faiss  # type: ignore
except ImportError:  # pragma: no cover - 런타임에서 안내
    faiss = None  # type: ignore

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

LOG = logging.getLogger(__name__)


def _resolve_api_key(explicit: Optional[str]) -> str:
    """프로젝트 규칙에 맞춰 OpenAI API 키를 찾는다."""
    if explicit:
        return explicit
    return get_openai_api_key()


def _ensure_faiss() -> None:
    if faiss is None:  # type: ignore[name-defined]
        raise RuntimeError(
            "FAISS is not available. Install the 'faiss-cpu' package and restart the app."
        )


def _stringify_collection(values: Iterable[Any]) -> str:
    """리스트 값을 검색용 문자열로 직렬화한다."""
    parts: List[str] = []
    for item in values:
        if isinstance(item, dict):
            label = str(item.get("item", "")).strip()
            importance = item.get("importance")
            if label and importance is not None:
                parts.append(f"{label} (importance={importance})")
            elif label:
                parts.append(label)
            else:
                parts.append(json.dumps(item, ensure_ascii=False))
        else:
            parts.append(str(item))
    return ", ".join(p for p in parts if p)


class VectorStore:
    """OpenAI 임베딩 + FAISS 기반 벡터 저장소."""

    def __init__(
        self,
        storage_dir: Optional[str | Path] = None,
        *,
        index_path: Optional[str | Path] = None,
        meta_path: Optional[str | Path] = None,
        api_key: Optional[str] = None,
    ) -> None:
        _ensure_faiss()
        base_dir = Path(storage_dir or "data/vector_store")
        base_dir.mkdir(parents=True, exist_ok=True)

        self.index_path = Path(index_path) if index_path else base_dir / "faiss.index"
        self.meta_path = Path(meta_path) if meta_path else base_dir / "metadata.jsonl"

        self._client: Optional[OpenAI] = None
        self._api_key = api_key
        self.index: Optional[Any] = None
        self.metadata: List[Dict[str, Any]] = []

        self._load_index()
        self._load_metadata()
        self._align_index_and_metadata()

    # 지연 초기화된 OpenAI 클라이언트
    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=_resolve_api_key(self._api_key))
        return self._client

    def _load_index(self) -> None:
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))  # type: ignore[arg-type]

    def _load_metadata(self) -> None:
        if not self.meta_path.exists():
            return
        with self.meta_path.open("r", encoding="utf-8") as handle:
            self.metadata = [json.loads(line) for line in handle if line.strip()]

    def _align_index_and_metadata(self) -> None:
        if self.index is None:
            if self.metadata:
                LOG.warning(
                    "Metadata found without a FAISS index. Run `rebuild_index` to regenerate vectors."
                )
            return

        ntotal = self.index.ntotal
        meta_len = len(self.metadata)
        if ntotal == meta_len:
            return

        if meta_len > ntotal:
            LOG.warning("Truncating metadata from %s to match %s vectors.", meta_len, ntotal)
            self.metadata = self.metadata[:ntotal]
        else:
            LOG.warning(
                "Loaded index has more vectors (%s) than metadata entries (%s). "
                "Consider rebuilding the index to avoid mismatched results.",
                ntotal,
                meta_len,
            )

    def _ensure_index(self) -> Any:
        if self.index is None:
            self.index = faiss.IndexFlatIP(EMBED_DIM)
        return self.index

    # 인덱스/메타데이터 저장
    def _write_index(self) -> None:
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_path))  # type: ignore[arg-type]

    def _append_metadata(self, records: Iterable[Dict[str, Any]]) -> None:
        with self.meta_path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 임베딩 생성 및 검색 핵심 동작
    def _embed(self, texts: List[str]) -> np.ndarray:
        response = self.client.embeddings.create(model=EMBED_MODEL, input=texts)
        vectors = [item.embedding for item in response.data]
        return np.asarray(vectors, dtype="float32")

    def add(self, docs: List[Dict[str, Any]]) -> None:
        if not docs:
            return

        texts = [doc["text"] for doc in docs]
        embeddings = self._embed(texts)
        faiss.normalize_L2(embeddings)

        index = self._ensure_index()
        index.add(embeddings)

        self.metadata.extend(docs)
        self._append_metadata(docs)
        self._write_index()

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if not query.strip():
            return []
        if self.index is None or not self.metadata:
            return []

        query_vec = self._embed([query])
        faiss.normalize_L2(query_vec)
        distances, indices = self._ensure_index().search(query_vec, k)

        results: List[Dict[str, Any]] = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            item = dict(self.metadata[idx])
            item["score"] = float(score)
            results.append(item)
        return results

    # ai_utils 결과 포맷을 인덱싱 가능한 문서로 변환
    def add_objective_results(
        self,
        items: Iterable[tuple[str, Dict[str, Any]]],
        *,
        use_normalized_fields: bool = True,
    ) -> None:
        """`(문서 ID, objective_result)` 튜플 목록을 문서로 변환해 추가한다."""
        docs: List[Dict[str, Any]] = []
        for doc_id, payload in items:
            text = format_objective_result_text(payload, use_normalized_fields=use_normalized_fields)
            if not text:
                continue
            metadata = {
                "id": doc_id,
                "content_type": payload.get("content_type"),
                "source": payload,
            }
            docs.append({"id": doc_id, "text": text, "metadata": metadata})

        if docs:
            self.add(docs)

    # 유지보수
    def rebuild_index(self) -> None:
        """저장된 메타데이터 기준으로 FAISS 인덱스를 재생성한다."""
        if not self.metadata:
            self.index = None
            if self.index_path.exists():
                self.index_path.unlink()
            return

        texts = [record["text"] for record in self.metadata]
        embeddings = self._embed(texts)
        faiss.normalize_L2(embeddings)

        self.index = faiss.IndexFlatIP(EMBED_DIM)
        self.index.add(embeddings)
        self._write_index()


def format_objective_result_text(
    objective: Dict[str, Any],
    *,
    use_normalized_fields: bool = True,
) -> str:
    """objective 분석 결과를 검색 가능한 텍스트로 변환한다."""
    if not objective:
        return ""

    fields = ["main_topics", "entities", "keywords"]
    lines: List[str] = []

    content_type = objective.get("content_type")
    if content_type:
        lines.append(f"content_type: {content_type}")

    for field in fields:
        value = objective.get(field)
        if not value and not use_normalized_fields:
            value = objective.get(f"{field}_raw")
        if not value:
            continue
        text = _stringify_collection(value if isinstance(value, list) else [value])
        if text:
            lines.append(f"{field}: {text}")

    # 프로파일 요약/메모가 있으면 함께 포함
    summary = objective.get("profiler_summary")
    if summary:
        lines.append(f"summary: {summary}")

    extra_notes = objective.get("notes")
    if extra_notes:
        lines.append(f"notes: {extra_notes}")

    return "\n".join(lines)
