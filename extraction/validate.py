import argparse, json, pathlib, sys

SHORT_SECTION = 200  # below this many chars its worth double checking if its actually a section or a mistake.


def validate(out_dir):
    manifest = out_dir / "chunks.json"
    if not manifest.exists():
        raise SystemExit(f"no chunks.json in {out_dir}, run extract.py first")

    chunks = json.loads(manifest.read_text(encoding="utf-8"))
    on_disk = {p.name for p in (out_dir / "images").glob("*.png")}
    referenced = {f for c in chunks for f in c["figures"]}

    problems = []

    missing = referenced - on_disk
    if missing:
        problems.append(f"referenced but not on disk: {', '.join(sorted(missing))}")

    orphans = on_disk - referenced
    if orphans:
        print(f"note: {len(orphans)} image(s) on disk with no reference")

    short = [c["section"] for c in chunks if len(c["content"]) < SHORT_SECTION]
    if short:
        problems.append(f"suspiciously short: {', '.join(short)}")

    nulls = [c["section"] for c in chunks if c["page"] is None]
    if nulls:
        print(f"note: no page number for {', '.join(nulls)}")

    lengths = sorted(len(c["content"]) for c in chunks)
    print(f"\n{len(chunks)} sections, {len(on_disk)} images")
    print(f"content length: min {lengths[0]}, median {lengths[len(lengths)//2]}, "
          f"max {lengths[-1]}")

    if problems:
        print("\nproblems:")
        for p in problems:
            print(f"  {p}")
        return 1
    print("\nlooks fine")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=pathlib.Path)
    a = ap.parse_args()
    sys.exit(validate(a.out_dir))