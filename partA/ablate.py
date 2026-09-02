#!/usr/bin/env python3
"""
ablate.py -- isolate every claimed flaw in fertility.py and measure its effect.

This exists to satisfy the evidence rule. Each flaw is a single boolean/enum
knob. We compute the report's headline number (the hin/eng fertility ratio)
with v0 behaviour, then flip exactly one knob at a time, and print the delta.
A knob that moves nothing is evidence the "flaw" is harmless -- that is a
result, not a failure.

Usage:
    # real run (needs tiktoken and/or transformers + network)
    python ablate.py --corpus corpus/ --tokenizer gpt2 --base eng --lang hin

    # harness self-test with a deterministic stub tokenizer, no network.
    # Numbers from this mode are NOT results -- they only prove the plumbing.
    python ablate.py --corpus ../../starter_kit/corpus_sample --tokenizer mock \
                     --base eng --lang hin --files eng=eng_sample.txt,hin=hin_sample.txt
"""
import argparse, os, sys, unicodedata
from dataclasses import dataclass, replace

try:
    import regex as _re
    GRAPHEME = lambda s: len(_re.findall(r"\X", s))
except ImportError:
    sys.exit("pip install regex  (needed for grapheme-cluster denominator)")


# ---------------------------------------------------------------- tokenizers
def load_tokenizer(spec):
    if spec == "mock":
        # Deterministic stand-in: ~1 token per UTF-8 byte for codepoints outside
        # Latin-1, ~1 token per 4 bytes inside it. Mimics the *shape* of a
        # byte-level BPE with an English-only vocab. For plumbing tests only.
        def enc(s):
            n = 0
            for ch in s:
                n += len(ch.encode()) if ord(ch) > 0xFF else 0.25
            return [0] * max(1, round(n))
        return enc
    if spec.startswith("hf:"):
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(spec[3:])
        return lambda s: tok.encode(s, add_special_tokens=False)
    import tiktoken
    return tiktoken.get_encoding(spec).encode


# ---------------------------------------------------------------- knobs
@dataclass(frozen=True)
class Cfg:
    lower: bool = True          # F1  v0 lowercases before tokenizing
    split: str = "literal"      # F2  v0 uses .split(" ") not .split()
    agg: str = "macro"          # F4  v0 averages per-line ratios
    denom: str = "word"         # F5  v0 offers word / codepoint only
    nfc: bool = True            # H1  v0 applies NFC (claimed harmless)
    seed: bool = True           # H2  v0 seeds `random` (claimed harmless)


V0 = Cfg()
FIXED = Cfg(lower=False, split="whitespace", agg="micro", denom="sentence", nfc=True, seed=False)


def read_lines(path, cfg):
    out = []
    for raw in open(path, encoding="utf-8"):
        line = raw.strip()
        if not line:
            continue
        if cfg.nfc:
            line = unicodedata.normalize("NFC", line)
        out.append(line)
    return out


def denominator(line, cfg):
    if cfg.denom == "word":
        return len(line.split(" ")) if cfg.split == "literal" else len(line.split())
    if cfg.denom == "codepoint":
        return len(line)
    if cfg.denom == "grapheme":
        return GRAPHEME(line)
    if cfg.denom == "byte":
        return len(line.encode())
    if cfg.denom == "sentence":
        return 1
    raise ValueError(cfg.denom)


def measure(lines, encode, cfg):
    if cfg.seed:
        import random
        random.seed(1337)
    num = den = 0
    ratios = []
    for line in lines:
        s = line.lower() if cfg.lower else line
        t = len(encode(s))
        d = denominator(s, cfg)
        num += t
        den += d
        ratios.append(t / d)
    return (sum(ratios) / len(ratios)) if cfg.agg == "macro" else (num / den)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="directory of <lang>.txt")
    ap.add_argument("--files", default=None, help="override, e.g. eng=a.txt,hin=b.txt")
    ap.add_argument("--tokenizer", default="gpt2")
    ap.add_argument("--base", default="eng")
    ap.add_argument("--lang", default="hin")
    args = ap.parse_args()

    if args.files:
        paths = {k: os.path.join(args.corpus, v)
                 for k, v in (p.split("=", 1) for p in args.files.split(","))}
    else:
        paths = {args.base: os.path.join(args.corpus, f"{args.base}.txt"),
                 args.lang: os.path.join(args.corpus, f"{args.lang}.txt")}

    encode = load_tokenizer(args.tokenizer)
    if args.tokenizer == "mock":
        print("!! MOCK TOKENIZER -- plumbing self-test only, not a result !!\n")

    def ratio(cfg):
        b = measure(read_lines(paths[args.base], cfg), encode, cfg)
        l = measure(read_lines(paths[args.lang], cfg), encode, cfg)
        return b, l, l / b

    b0, l0, r0 = ratio(V0)
    print(f"tokenizer: {args.tokenizer}   base={args.base} lang={args.lang}")
    print(f"v0 baseline: {args.base}={b0:.4f}  {args.lang}={l0:.4f}  ratio={r0:.4f}\n")

    knobs = [
        ("F1  lower=False        (stop lowercasing)",       dict(lower=False)),
        ("F2  split=whitespace   (fix .split(' '))",        dict(split="whitespace")),
        ("F4  agg=micro          (corpus-level, not macro)", dict(agg="micro")),
        ("F5a denom=grapheme",                               dict(denom="grapheme")),
        ("F5b denom=byte",                                   dict(denom="byte")),
        ("F5c denom=sentence     (parallel-sentence)",       dict(denom="sentence")),
        ("H1  nfc=False          (claimed HARMLESS)",        dict(nfc=False)),
        ("H2  seed removed       (claimed HARMLESS)",        dict(seed=False)),
    ]

    print(f"{'knob (one at a time vs v0)':<44}{'base':>9}{'lang':>9}{'ratio':>9}{'d_ratio':>10}{'d%':>9}")
    print("-" * 90)
    for label, kw in knobs:
        b, l, r = ratio(replace(V0, **kw))
        print(f"{label:<44}{b:>9.4f}{l:>9.4f}{r:>9.4f}{r-r0:>+10.4f}{100*(r/r0-1):>+8.2f}%")

    bf, lf, rf = ratio(FIXED)
    print("-" * 90)
    print(f"{'ALL FIXES (micro, no-lower, per-sentence)':<44}{bf:>9.4f}{lf:>9.4f}{rf:>9.4f}"
          f"{rf-r0:>+10.4f}{100*(rf/r0-1):>+8.2f}%")
    print("\nInterpretation: any row with d% == 0.00 is a knob that does nothing.")
    print("Those are the 'looks suspicious but is fine' candidates -- do not claim them as bugs.")


if __name__ == "__main__":
    main()
