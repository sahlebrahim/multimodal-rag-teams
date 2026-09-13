import argparse, base64, json, os, pathlib, re, time
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI

PROMPT = """transcribe this figure for a search index. state every number, label and
identifier exactly as shown. describe position only where it carries meaning, such as
which zone a device sits in. reply with one dense paragraph of plain prose, no markdown,
no lists, no preamble.

the section text around the image is background only, so you know what the document calls
things. describe what is visible in the image and nothing else. do not repeat a claim from
the section text as if you had observed it, and do not judge condition, quality, alignment
or compliance."""

MEDIA = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif"}

img_ref = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def client():
    load_dotenv()
    token = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_ad_token_provider=token,
        api_version="2024-10-21",
    )


def describe(api, img, context):
    b64 = base64.b64encode(img.read_bytes()).decode()
    media = MEDIA.get(img.suffix.lower(), "image/png")
    r = api.chat.completions.create(
        model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": f"{PROMPT}\n\nsection text:\n\n{context}"},
                {"type": "image_url", "image_url": {"url": f"data:{media};base64,{b64}"}},
            ],
        }],
    )
    return r.choices[0].message.content.strip()


def jobs(chunks):
    # a chunk is already one section, so the whole chunk is the context. the image ref becomes a marker so the model can see where in the section it sits.
    out = []
    for c in chunks:
        for m in img_ref.finditer(c["content"]):
            name = pathlib.Path(m.group(1)).name
            context = c["content"].replace(m.group(0), "[IMAGE APPEARS HERE]")
            out.append((name, context))
    return out


def describe_all(api, out_dir, work):
    cache_file = out_dir / "descriptions.json"
    if cache_file.exists():
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
    else:
        cache = {}

    for n, (name, context) in enumerate(work, 1):
        if name in cache:
            continue
        img = out_dir / "images" / name
        if not img.exists():
            print(f"[{n}/{len(work)}] {name} not on disk, skipping")
            continue
        try:
            cache[name] = describe(api, img, context)
            print(f"[{n}/{len(work)}] {name}")
        except Exception as e:
            print(f"[{n}/{len(work)}] {name} failed: {e}")
            continue
        # saved after each one so a crash halfway doesn't throw away paid work
        cache_file.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
        time.sleep(1)

    return cache


def rewrite(content, cache):
    def block(m):
        name = pathlib.Path(m.group(1)).name
        if name not in cache:
            return m.group(0)
        return (f"[Image Content Extracted]\nFIGURE_FILE = {name}\n"
                f"{cache[name]}\n[End of Image Content]")

    return img_ref.sub(block, content)


def write_sample(out_dir, cache, n):
    blocks = []
    for name, desc in list(cache.items())[:n]:
        path = (out_dir / "images" / name).as_posix()
        blocks.append(f"## {name}\n\n![]({path})\n\n{desc}\n")
    (out_dir / "sample.md").write_text("\n".join(blocks), encoding="utf-8")


def enrich(out_dir, sample):
    chunks = json.loads((out_dir / "chunks.json").read_text(encoding="utf-8"))

    work = jobs(chunks)
    cache = describe_all(client(), out_dir, work)

    for c in chunks:
        if c["figures"]:
            c["content"] = rewrite(c["content"], cache)

    (out_dir / "chunks.enriched.json").write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if sample:
        write_sample(out_dir, cache, sample)
        print("sample.md written, check the numbers against the pdf")

    print(f"{len(cache)} of {len(work)} figures described")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=pathlib.Path)
    ap.add_argument("--sample", type=int, default=0)
    a = ap.parse_args()
    enrich(a.out_dir, a.sample)