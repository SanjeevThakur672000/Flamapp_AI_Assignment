#!/usr/bin/env python3
"""
fertility_fixed.py -- corrected cross-language tokenizer cost analysis.

Differences from fertility.py v0, each justified in AUDIT.md:
  - no lowercasing (v0 applied an asymmetric transform: it mutates Latin text
    and is a no-op on every Indic script, so it biases exactly the comparison
    the report is making)
  - .split() not .split(" ")
  - corpus-level micro-averages (sum tokens / sum denominators), not the mean
    of per-line ratios
  - four denominators side by side: whitespace word, grapheme cluster,
    UTF-8 byte, and parallel sentence
  - a token-premium column: tokens_lang / tokens_eng over the *same* aligned
    sentences. This is the number that should drive routing and cost.
  - requires the input files to be line-aligned and refuses to run otherwise

Usage:
    python fertility_fixed.py --corpus corpus/ \
        --tokenizer gpt2 --tokenizer cl100k_base --tokenizer o200k_base \
        --tokenizer hf:xlm-roberta-base --tokenizer hf:google/muril-base-cased
"""
import argparse, json, sys, unicodedata
from collections import OrderedDict

try:
    import regex as _re
except ImportError:
    sys.exit("pip install regex")

LANG_ORDER = ["eng", "hin", "ben", "mar", "kan", "tam", "tel", "mal"]


def load_tokenizer(spec):
    if spec.startswith("hf:"):
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(spec[3:])
        return lambda s: tok.encode(s, add_special_tokens=False)
    import tiktoken
    return tiktoken.get_encoding(spec).encode


def read(path):
    lines = [unicodedata.normalize("NFC", l.strip())
             for l in open(path, encoding="utf-8") if l.strip()]
    return lines


def counts(lines):
    return dict(
        sent=len(lines),
        word=sum(len(l.split()) for l in lines),
        graph=sum(len(_re.findall(r"\X", l)) for l in lines),
        byte=sum(len(l.encode()) for l in lines),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--tokenizer", action="append", required=True)
    ap.add_argument("--base", default="eng")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    corpora = OrderedDict()
    for lang in LANG_ORDER:
        p = f"{args.corpus.rstrip('/')}/{lang}.txt"
        try:
            corpora[lang] = read(p)
        except FileNotFoundError:
            continue
    if args.base not in corpora:
        sys.exit(f"base language {args.base} not found in {args.corpus}")

    n = {len(v) for v in corpora.values()}
    if len(n) != 1:
        sys.exit(f"corpus is NOT line-aligned: {[(k, len(v)) for k, v in corpora.items()]}\n"
                 "Per-sentence comparison is invalid on unaligned data. Aborting.")
    print(f"corpus: {args.corpus}  |  {len(corpora)} languages x {n.pop()} aligned sentences\n")

    out = {}
    for spec in args.tokenizer:
        encode = load_tokenizer(spec)
        toks = {l: sum(len(encode(s)) for s in ls) for l, ls in corpora.items()}
        cnt = {l: counts(ls) for l, ls in corpora.items()}
        base_tok = toks[args.base]

        print(f"### tokenizer: {spec}")
        print(f"{'lang':<6}{'tok/word':>10}{'tok/graph':>11}{'tok/byte':>10}"
              f"{'tok/sent':>10}{'PREMIUM vs '+args.base:>18}")
        print("-" * 65)
        for l in corpora:
            c = cnt[l]
            prem = toks[l] / base_tok
            print(f"{l:<6}{toks[l]/c['word']:>10.3f}{toks[l]/c['graph']:>11.3f}"
                  f"{toks[l]/c['byte']:>10.3f}{toks[l]/c['sent']:>10.2f}{prem:>18.2f}x")
        print()
        out[spec] = {l: dict(tokens=toks[l], premium=toks[l] / base_tok, **cnt[l])
                     for l in corpora}

    if len(args.tokenizer) > 1:
        print("### token premium vs eng, by tokenizer  (the routing number)")
        hdr = f"{'lang':<6}" + "".join(f"{s.replace('hf:',''):>26}" for s in args.tokenizer)
        print(hdr); print("-" * len(hdr))
        for l in corpora:
            row = f"{l:<6}"
            for s in args.tokenizer:
                row += f"{out[s][l]['premium']:>25.2f}x"
            print(row)
        print("\nIf the premium falls materially across columns for the same language,")
        print("the cost is a property of the TOKENIZER, not of the script.")

    if args.json:
        json.dump(out, open(args.json, "w"), indent=2)
        print(f"\n[+] wrote {args.json}")


if __name__ == "__main__":
    main()
