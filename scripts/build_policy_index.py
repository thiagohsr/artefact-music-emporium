import contextlib
import hashlib
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from emporio.data.policy_index import (
    INDEX_PATH,
    embed_with_ollama,
    embed_with_openrouter,
    encode_vector,
    ollama_embedding_model,
    openrouter_embedding_model,
    read_settings,
)

PDF_PATH = INDEX_PATH.parent / "políticas_da_loja.pdf"
RUNNING_HEADER = "Empório da Música Manual de Políticas e Procedimentos"
PAGE_MARKER = re.compile(r"^Página \d+$")
HEADING = re.compile(r"^(\d{1,2})(?:\.(\d{1,2})|\.)\s+(\S.*)$")
# Section 7 instructs the attendant and section 10 is about the manual itself.
STAFF_SECTIONS = {"7", "10"}

SCHEMA = """
CREATE TABLE policy_sections (
    number TEXT PRIMARY KEY,
    parent TEXT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    page INTEGER NOT NULL,
    audience TEXT NOT NULL CHECK (audience IN ('customer', 'staff'))
) STRICT;

CREATE TABLE policy_vectors (
    number TEXT PRIMARY KEY REFERENCES policy_sections (number),
    embedding BLOB NOT NULL
) STRICT;

CREATE VIRTUAL TABLE policy_fts USING fts5(
    number UNINDEXED, title, body, tokenize = 'unicode61 remove_diacritics 2'
);

CREATE TABLE index_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) STRICT;
"""


@dataclass
class Section:
    number: str
    parent: str | None
    title: str
    page: int
    lines: list[str]

    @property
    def body(self) -> str:
        return "\n".join(self.lines)

    @property
    def audience(self) -> str:
        return "staff" if self.number.split(".")[0] in STAFF_SECTIONS else "customer"


def parse_sections(pages: list[str]) -> list[Section]:
    """Numbers must advance in order, so a numbered list inside a section is not read as a heading."""
    sections: list[Section] = []
    current_top = 0
    for page_number, page in enumerate(pages, start=1):
        for raw_line in page.splitlines():
            line = " ".join(raw_line.split())
            if not line or line == RUNNING_HEADER or PAGE_MARKER.match(line):
                continue
            heading = HEADING.match(line)
            if heading:
                top, sub, title = int(heading[1]), heading[2], heading[3]
                if sub is None and top == current_top + 1:
                    current_top = top
                    sections.append(Section(str(top), None, title, page_number, []))
                    continue
                if sub is not None and top == current_top:
                    sections.append(Section(f"{top}.{sub}", str(top), title, page_number, []))
                    continue
            if sections:
                sections[-1].lines.append(line)
    return sections


def embedding_text(section: Section, titles: dict[str, str]) -> str:
    heading = f"{section.number} {section.title}"
    if section.parent:
        heading = f"{titles[section.parent]} > {heading}"
    return f"{heading}\n{section.body}"


def embed(texts: list[str]) -> tuple[list[list[float]], str, str]:
    settings = read_settings()
    if settings.get("OLLAMA_BASE_URL"):
        return embed_with_ollama(texts, settings), "ollama", ollama_embedding_model(settings)
    if settings.get("OPENROUTER_API_KEY"):
        return embed_with_openrouter(texts, settings), "openrouter", openrouter_embedding_model(settings)
    sys.exit("Set OLLAMA_BASE_URL or OPENROUTER_API_KEY to build the policy index.")


def write_index(path: Path, sections: list[Section], vectors: list[list[float]], metadata: dict[str, str]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.unlink(missing_ok=True)
    with contextlib.closing(sqlite3.connect(temporary)) as conn:
        conn.executescript(SCHEMA)
        with conn:
            conn.executemany(
                "INSERT INTO policy_sections VALUES (?, ?, ?, ?, ?, ?)",
                [(s.number, s.parent, s.title, s.body, s.page, s.audience) for s in sections],
            )
            searchable = [section for section in sections if section.body]
            for section, vector in zip(searchable, vectors, strict=True):
                conn.execute("INSERT INTO policy_vectors VALUES (?, ?)", (section.number, encode_vector(vector)))
                conn.execute(
                    "INSERT INTO policy_fts VALUES (?, ?, ?)", (section.number, section.title, section.body)
                )
            conn.executemany("INSERT INTO index_metadata VALUES (?, ?)", metadata.items())
        conn.execute("VACUUM")
    temporary.replace(path)


def main() -> None:
    reader = PdfReader(PDF_PATH)
    sections = parse_sections([page.extract_text(extraction_mode="layout") for page in reader.pages])
    titles = {section.number: f"{section.number} {section.title}" for section in sections}
    # Sections 5, 6 and 8 only group their subsections, so a search must not return their empty bodies.
    vectors, provider, model = embed([embedding_text(s, titles) for s in sections if s.body])
    write_index(
        INDEX_PATH,
        sections,
        vectors,
        {
            "provider": provider,
            "model": model,
            "dimensions": str(len(vectors[0])),
            "source_sha256": hashlib.sha256(PDF_PATH.read_bytes()).hexdigest(),
        },
    )
    print(f"{INDEX_PATH.name}: {len(sections)} sections, {len(vectors[0])} dimensions, {provider} {model}")


if __name__ == "__main__":
    main()
