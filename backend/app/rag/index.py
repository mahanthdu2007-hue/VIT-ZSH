"""§12 Chroma index: one document per career, pathway, scholarship and exam.

Rebuild with `python -m app.rag.index`. Metadata is `{kind, id, career_id}`; scholarships and exams are not tied
to one career, so their career_id is empty. If the index is missing or Chroma fails, the same documents are built
from the dataset in memory, so explanations never depend on the index being present (§2.4).
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from app.engine import config
from app.engine.formatting import format_inr
from app.engine.loader import get_dataset
from app.models.schemas import Career, Citation, Dataset, Exam, Pathway, Scholarship

CHROMA_DIR = Path(__file__).resolve().parents[2] / "chroma"
COLLECTION = "prism_dataset"
DocKind = Literal["career", "pathway", "scholarship", "exam"]


@dataclass(frozen=True)
class IndexDoc:
    doc_id: str
    kind: DocKind
    id: str
    career_id: str
    label: str
    text: str


def _lpa(band: tuple[float, float]) -> str:
    return f"{band[0]:g}–{band[1]:g} LPA"


def career_doc(c: Career) -> IndexDoc:
    skills = ", ".join(s.name for s in c.skills)
    cities = sorted(c.city_demand.items(), key=lambda kv: -kv[1])[:3]
    text = (f"{c.name} ({c.domain}). {c.summary} Key skills: {skills}. Indicative salary: entry "
            f"{_lpa(c.salary_inr_lpa.entry)}, mid {_lpa(c.salary_inr_lpa.mid)}, senior {_lpa(c.salary_inr_lpa.senior)}. "
            f"Growth index {c.growth_index:g}, Job Velocity {c.job_velocity:g}, Economic Disruption Index "
            f"{c.disruption_index:g}. Highest city demand: "
            + ", ".join(f"{city} {value:g}" for city, value in cities)
            + f". Sources: {'; '.join(c.sources)}. {c.data_note}")
    return IndexDoc(f"career:{c.id}", "career", c.id, c.id, c.name, text)


def pathway_doc(c: Career, p: Pathway, exam_names: dict[str, str]) -> IndexDoc:
    exams = ", ".join(exam_names.get(e, e) for e in p.entrance_exams) or "none"
    text = (f"{c.name} route: {p.label} ({p.institution_type}, entry {p.entry.replace('_', ' ')}). "
            f"Steps: {' → '.join(p.steps)}. About {p.duration_years:g} years. Indicative cost "
            f"{format_inr(p.cost_inr.min)} to {format_inr(p.cost_inr.max)}. Entrance exams: {exams}.")
    return IndexDoc(f"pathway:{c.id}:{p.id}", "pathway", p.id, c.id, p.label, text)


def scholarship_doc(s: Scholarship) -> IndexDoc:
    income = f"family income up to {format_inr(s.income_max_inr)}" if s.income_max_inr else "no income limit"
    who = f" Only for {s.restricted_to}." if s.restricted_to else ""
    text = (f"{s.name} by {s.provider}: up to {format_inr(s.amount_inr_per_year)} a year, {income}. "
            f"Levels: {', '.join(s.levels)}. Fields: {', '.join(s.domains)}.{who} Source: {s.source}.")
    return IndexDoc(f"scholarship:{s.id}", "scholarship", s.id, "", s.name, text)


def exam_doc(e: Exam) -> IndexDoc:
    text = (f"{e.name}: {e.level} level entrance exam for {', '.join(e.domains)}, usually in {e.typical_month}. "
            f"Source: {e.source}.")
    return IndexDoc(f"exam:{e.id}", "exam", e.id, "", e.name, text)


def build_documents(data: Dataset) -> list[IndexDoc]:
    exam_names = {e.id: e.name for e in data.exams}
    docs = [career_doc(c) for c in data.careers]
    docs += [pathway_doc(c, p, exam_names) for c in data.careers for p in c.pathways]
    docs += [scholarship_doc(s) for s in data.scholarships]
    docs += [exam_doc(e) for e in data.exams]
    return docs


@lru_cache
def dataset_documents() -> dict[str, IndexDoc]:
    """Every document built from the cached dataset, by document id."""
    return {d.doc_id: d for d in build_documents(get_dataset())}


def citation(doc_id: str) -> Citation:
    doc = dataset_documents()[doc_id]
    return Citation(kind=doc.kind, id=doc.id, career_id=doc.career_id or None, label=doc.label, text=doc.text)


def _embedding_function() -> Any:
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    return SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL)


def rebuild(data: Dataset, path: Path = CHROMA_DIR) -> int:
    """Drop and rebuild the collection; returns the number of documents."""
    import chromadb
    client = chromadb.PersistentClient(path=str(path))
    if COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    collection = client.create_collection(COLLECTION, embedding_function=_embedding_function())
    docs = build_documents(data)
    collection.add(ids=[d.doc_id for d in docs], documents=[d.text for d in docs],
                   metadatas=[{"kind": d.kind, "id": d.id, "career_id": d.career_id} for d in docs])
    return len(docs)


@lru_cache
def _collection() -> Any:
    import chromadb
    if not CHROMA_DIR.exists():
        return None
    try:
        return chromadb.PersistentClient(path=str(CHROMA_DIR)).get_collection(
            COLLECTION, embedding_function=_embedding_function())
    except Exception:  # missing collection or a broken index: use the dataset instead
        return None


def _from_chroma(rows: dict[str, Any]) -> list[IndexDoc]:
    labels = dataset_documents()
    return [IndexDoc(doc_id, m["kind"], m["id"], m["career_id"], labels[doc_id].label if doc_id in labels else m["id"],
                     text)
            for doc_id, m, text in zip(rows["ids"], rows["metadatas"], rows["documents"], strict=True)]


def retrieve(career_ids: list[str], linked_doc_ids: list[str]) -> tuple[list[IndexDoc], Literal["chroma", "dataset"]]:
    """§12 filtered retrieval: every document of these careers (`where career_id $in ids`) plus the scholarship
    and exam documents the engine linked to them. Returns the documents and where they came from."""
    collection = _collection()
    if collection is not None:
        try:
            docs = _from_chroma(collection.get(where={"career_id": {"$in": career_ids}},
                                               include=["documents", "metadatas"]))
            if linked_doc_ids:
                docs += _from_chroma(collection.get(ids=linked_doc_ids, include=["documents", "metadatas"]))
            return sorted(docs, key=lambda d: d.doc_id), "chroma"
        except Exception:  # Chroma failed mid-query: fall through to the dataset
            pass
    wanted = set(linked_doc_ids)
    docs = [d for d in dataset_documents().values() if d.career_id in career_ids or d.doc_id in wanted]
    return sorted(docs, key=lambda d: d.doc_id), "dataset"


def main() -> None:
    count = rebuild(get_dataset())
    print(f"Indexed {count} documents into {CHROMA_DIR} (collection {COLLECTION}).")


if __name__ == "__main__":
    main()
