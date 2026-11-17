"""Sync knowledge_base/*.md into the knowledge_base table.

The files are the source of truth: rows are inserted or updated, and rows whose
file or ## heading no longer exists are deleted.

Run from anywhere:  uv run python -m scripts.seed_knowledge_base
"""

from pathlib import Path

from app import db

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"


def parse(path: Path) -> list[tuple[str, str, str]]:
    """Split a section file into (section, title, content) rows, one per ## heading."""
    # Leading "\n" so a "## " on the very first line is also split off.
    text = "\n" + path.read_text(encoding="utf-8")
    entries = []
    for block in text.split("\n## ")[1:]:
        title, _, content = block.partition("\n")
        entries.append((path.stem, title.strip(), content.strip()))
    return entries


def main() -> None:
    entries = [entry for path in sorted(KB_DIR.glob("*.md")) for entry in parse(path)]
    if not entries:
        # An empty sync would delete every row; refuse instead.
        raise SystemExit(f"No ## sections found in {KB_DIR}, nothing synced.")

    with db.connect() as conn, conn.transaction():
        for section, title, content in entries:
            conn.execute(
                """
                insert into knowledge_base (section, title, content) values (%s, %s, %s)
                on conflict (section, title) do update
                  set content = excluded.content, updated_at = now()
                  where knowledge_base.content is distinct from excluded.content
                """,
                (section, title, content),
            )
        deleted = conn.execute(
            """
            delete from knowledge_base kb
            where not exists (
              select 1 from unnest(%s::text[], %s::text[]) as f(section, title)
              where f.section = kb.section and f.title = kb.title
            )
            returning section, title
            """,
            ([e[0] for e in entries], [e[1] for e in entries]),
        ).fetchall()

    for section in sorted({e[0] for e in entries}):
        print(f"{section}: {sum(e[0] == section for e in entries)} entries")
    for row in deleted:
        print(f"deleted stale: {row['section']} / {row['title']}")


if __name__ == "__main__":
    main()
