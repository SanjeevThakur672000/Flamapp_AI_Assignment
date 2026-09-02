#!/usr/bin/env python3
"""
build_corpus.py -- assemble the A1 multilingual eval corpus.

Primary source: FLORES-200 devtest (Meta/NLLB). 1012 sentences, professionally
translated from English Wikipedia-derived source text, aligned line-by-line
across all 200 languages. Line N in every file is the same sentence.

Why FLORES-200:
  - genuinely parallel (this is the whole point -- see AUDIT.md, flaw F3)
  - covers all languages Part C cares about
  - one file per language, plain UTF-8, no auth needed

Usage:
    python build_corpus.py --out corpus/          # downloads + extracts
    python build_corpus.py --out corpus/ --split dev

NOTE: I could not execute the download in the environment where this was
drafted (network egress blocked). Run it and record the actual line counts
and sha256 in NOTEBOOK.md -- do not trust the numbers in the docstring.
"""
import argparse, hashlib, io, os, sys, tarfile, urllib.request

FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"

# 8 languages: the 4 the assignment requires (eng, hin + 2 Dravidian) plus the
# rest of the Part C launch list, so Part A's numbers feed Part C directly.
LANGS = {
    "eng": "eng_Latn",   # English      (Latin)
    "hin": "hin_Deva",   # Hindi        (Devanagari)  Indo-Aryan
    "ben": "ben_Beng",   # Bengali      (Bengali)     Indo-Aryan
    "mar": "mar_Deva",   # Marathi      (Devanagari)  Indo-Aryan
    "kan": "kan_Knda",   # Kannada      (Kannada)     Dravidian
    "tam": "tam_Taml",   # Tamil        (Tamil)       Dravidian
    "tel": "tel_Telu",   # Telugu       (Telugu)      Dravidian
    "mal": "mal_Mlym",   # Malayalam    (Malayalam)   Dravidian
}


def fetch(url: str) -> bytes:
    print(f"[*] GET {url}", file=sys.stderr)
    with urllib.request.urlopen(url, timeout=300) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="corpus")
    ap.add_argument("--split", default="devtest", choices=["dev", "devtest"])
    ap.add_argument("--cache", default="flores200_dataset.tar.gz")
    args = ap.parse_args()

    if os.path.exists(args.cache):
        blob = open(args.cache, "rb").read()
        print(f"[*] using cached {args.cache}", file=sys.stderr)
    else:
        blob = fetch(FLORES_URL)
        open(args.cache, "wb").write(blob)

    print(f"[*] tarball sha256 = {hashlib.sha256(blob).hexdigest()}", file=sys.stderr)
    os.makedirs(args.out, exist_ok=True)

    want = {f"{code}.{args.split}": short for short, code in LANGS.items()}
    found = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        for m in tf.getmembers():
            base = os.path.basename(m.name)
            if base in want:
                text = tf.extractfile(m).read().decode("utf-8")
                dst = os.path.join(args.out, f"{want[base]}.txt")
                open(dst, "w", encoding="utf-8").write(text)
                found[want[base]] = text

    if not found:
        sys.exit("no matching files in tarball -- inspect the archive layout")

    print(f"\n{'lang':<6}{'lines':>7}{'sha256[:12]':>16}", file=sys.stderr)
    counts = set()
    for short in LANGS:
        if short not in found:
            print(f"{short:<6}{'MISSING':>7}", file=sys.stderr)
            continue
        lines = [l for l in found[short].split("\n") if l.strip()]
        counts.add(len(lines))
        h = hashlib.sha256(found[short].encode()).hexdigest()[:12]
        print(f"{short:<6}{len(lines):>7}{h:>16}", file=sys.stderr)

    # This assert is the point of the whole script. If it fires, the corpus is
    # not parallel and every per-sentence number downstream is meaningless.
    assert len(counts) == 1, f"NOT LINE-ALIGNED: differing line counts {counts}"
    print(f"\n[+] {len(found)} languages, {counts.pop()} aligned sentences each", file=sys.stderr)


if __name__ == "__main__":
    main()
