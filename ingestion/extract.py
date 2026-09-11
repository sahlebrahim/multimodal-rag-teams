import argparse, json, pathlib, re
import pymupdf, pymupdf4llm

# tuned to the aislewatch playbook's page furniture. another doc needs its own.
STRIP = [
    (r"<!-- Start of picture text -->.*?<!-- End of picture text -->", re.S),
    (r"^\*\*AISLEWATCH.*?\*\*\s*$", re.M),
    (r"^AW-PB-001\s*\|.*$", re.M),
    (r"^#{0,6}\s*\*\*PUBLIC DEMONSTRATION EDITION\*\*\s*$", re.M),
    (r"^\d{2}\s*$", re.M),
]
# section number sits on its own line above the title, fold it into the heading
HEADING_MERGE = (r"^(?:#{1,6}\s+)?\*\*(\d{2})\*\*\s*\n+#\s+\*?\*?(.+?)\*?\*?\s*$", r"# \1 \2")
SKIP = {"front matter", "contents"}

img_ref = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
heading = re.compile(r"^#\s+(.*?)\s*$")


def toc_key(s):
    # toc strings and markdown headings disagree on punctuation and spacing
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def clean(md):
    for pat, flags in STRIP:
        md = re.sub(pat, "", md, flags=flags)
    return re.sub(HEADING_MERGE[0], HEADING_MERGE[1], md, flags=re.M)


def glue_table_rows(md):
    # tables sometimes wrap onto a second row with an empty first cell
    out = []
    for line in md.split("\n"):
        if line.startswith("||") and out and out[-1].startswith("|"):
            prev, curr = out[-1].split("|")[1:-1], line.split("|")[1:-1]
            out[-1] = "|" + "|".join(
                (p + " " + c).strip() if c.strip() else p
                for p, c in zip(prev, curr)
            ) + "|"
        else:
            out.append(line)
    return "\n".join(out)


def split_on_h1(md):
    sections, curr = [], {"title": "front matter", "lines": []}
    for line in md.split("\n"):
        m = heading.match(line)
        if m:
            sections.append(curr)
            curr = {"title": m.group(1).replace("**", "").strip(), "lines": []}
        else:
            curr["lines"].append(line)
    sections.append(curr)
    return sections


def extract(pdf, out_dir, doc_id):
    if not pdf.exists():
        raise SystemExit(f"no pdf at {pdf}")

    images = out_dir / "images"
    images.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(pdf)
    toc = {toc_key(t): p for _, t, p in doc.get_toc()}
    if not toc:
        print("no outline in this pdf, pages will be null")

    md = pymupdf4llm.to_markdown(
        pdf, write_images=True, image_path=str(images), image_format="png", dpi=150
    )
    md = glue_table_rows(clean(md))

    chunks = []
    for s in split_on_h1(md):
        title = s["title"]
        body = re.sub(r"\n{3,}", "\n\n", "\n".join(s["lines"])).strip()
        if not body or title.lower() in SKIP:
            continue
        chunks.append({
            "chunk_id": f"{doc_id}-{len(chunks):03d}",
            "section": title,
            "page": toc.get(toc_key(title)),
            "content": body,
            "figures": [pathlib.Path(f).name for f in img_ref.findall(body)],
            "sourcefile": pdf.name,
            "document_id": doc_id,
        })

    (out_dir / "chunks.json").write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"{len(chunks)} sections, {len(list(images.glob('*.png')))} images")
    nulls = [c["section"] for c in chunks if c["page"] is None]
    if nulls:
        print("no page for:", ", ".join(nulls))
    for c in chunks:
        print(f"  p{str(c['page'] or '?'):>2}  {len(c['content']):>5}  "
              f"{len(c['figures'])}fig  {c['section']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=pathlib.Path)
    ap.add_argument("out_dir", type=pathlib.Path)
    ap.add_argument("--doc-id", default="AW-PB-001")
    a = ap.parse_args()
    extract(a.pdf, a.out_dir, a.doc_id)