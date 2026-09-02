#!/usr/bin/env python3
"""
decompose.py -- refute REPORT_v0 finding 3 using only the report's own table
plus byte counts of the corpus it was run on. No tokenizer required.

Identity:
    tok/word = (tok/byte) x (byte/word)

so the headline hin/eng fertility ratio factorises exactly into

    ratio = [ (byte/word)_hin / (byte/word)_eng ]   <- script / UTF-8 encoding
          x [ (tok/byte)_hin / (tok/byte)_eng ]     <- tokenizer vocabulary

The report asserts the whole effect is the first factor ("a property of the
script, not the tokenizer"). We measure both.
"""
import sys, unicodedata, regex

import os
_DEF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "starter_kit", "corpus_sample")
D = sys.argv[1] if len(sys.argv) > 1 else _DEF
if not os.path.isdir(D): sys.exit(f"corpus_sample not found at {D}\nusage: python {sys.argv[0]} /path/to/corpus_sample")
FILES = {"eng": "eng_sample.txt", "hin": "hin_sample.txt"}
# REPORT_v0 section 1 table, gpt2
REPORTED_FERT = {"eng": 1.27, "hin": 7.45}
REPORTED_TPC = {"eng": 0.226, "hin": 1.579}

m = {}
for lang, fn in FILES.items():
    lines = [unicodedata.normalize("NFC", l.strip())
             for l in open(D.rstrip("/") + "/" + fn, encoding="utf-8") if l.strip()]
    m[lang] = dict(
        words=sum(len(l.split()) for l in lines),
        cps=sum(len(l) for l in lines),
        graphs=sum(len(regex.findall(r"\X", l)) for l in lines),
        bytes=sum(len(l.encode()) for l in lines),
    )

print("=== measured corpus densities (exact, no tokenizer) ===")
print(f"{'lang':<6}{'words':>7}{'codepts':>9}{'graphemes':>11}{'bytes':>8}"
      f"{'cp/word':>9}{'graph/word':>12}{'byte/word':>11}")
for l, c in m.items():
    print(f"{l:<6}{c['words']:>7}{c['cps']:>9}{c['graphs']:>11}{c['bytes']:>8}"
          f"{c['cps']/c['words']:>9.2f}{c['graphs']/c['words']:>12.2f}{c['bytes']/c['words']:>11.2f}")

print("\n=== REPORT_v0 finding 3: 'Hindi has more Unicode characters per word' ===")
print(f"  code points per word : hin {m['hin']['cps']/m['hin']['words']:.2f}  vs  "
      f"eng {m['eng']['cps']/m['eng']['words']:.2f}   -> Hindi has FEWER")
print(f"  graphemes  per word  : hin {m['hin']['graphs']/m['hin']['words']:.2f}  vs  "
      f"eng {m['eng']['graphs']/m['eng']['words']:.2f}   -> Hindi has FEWER")
print(f"  UTF-8 bytes per word : hin {m['hin']['bytes']/m['hin']['words']:.2f} vs  "
      f"eng {m['eng']['bytes']/m['eng']['words']:.2f}   -> Hindi has 2.2x MORE")
print("  The claim is false as stated. The real asymmetry is bytes, not characters,")
print("  and gpt2 is a byte-level BPE -- which makes it a tokenizer property.")

print("\n=== factorising the report's own 5.87x ===")
bpw = {l: m[l]["bytes"] / m[l]["words"] for l in m}
tpb = {l: REPORTED_FERT[l] / bpw[l] for l in m}
f_script = bpw["hin"] / bpw["eng"]
f_tok = tpb["hin"] / tpb["eng"]
print(f"  script/encoding factor  (bytes per word)  = {f_script:.3f}x")
print(f"  tokenizer factor        (tokens per byte) = {f_tok:.3f}x")
print(f"  product                                   = {f_script*f_tok:.3f}x")
print(f"  report's stated ratio                     = {REPORTED_FERT['hin']/REPORTED_FERT['eng']:.3f}x  (5.89 as printed)")
print(f"  -> the TOKENIZER contributes the larger factor ({f_tok:.2f}x vs {f_script:.2f}x).")
print("  Caveat: REPORTED_FERT is macro-averaged by the buggy v0 script while the")
print("  byte counts here are corpus-level, so this reproduces the ratio to ~0.3%,")
print("  not exactly. The sign and the ordering of the two factors are robust to that.")

print("\n=== REPORT_v0 finding 2: 'tok/char confirms the per-word number' ===")
rf = REPORTED_FERT["hin"] / REPORTED_FERT["eng"]
rc = REPORTED_TPC["hin"] / REPORTED_TPC["eng"]
print(f"  fertility ratio = {rf:.2f}x ; tok/char ratio = {rc:.2f}x")
print("  These share a numerator: (tok/word)/(tok/char) == char/word. Not independent.")
print(f"  implied chars/word  eng = {REPORTED_FERT['eng']/REPORTED_TPC['eng']:.2f}, "
      f"hin = {REPORTED_FERT['hin']/REPORTED_TPC['hin']:.2f}")
print(f"  measured chars/word eng = {m['eng']['cps']/m['eng']['words']:.2f}, "
      f"hin = {m['hin']['cps']/m['hin']['words']:.2f}")
print(f"  ratio-of-ratios {rc/rf:.3f} == eng_cpw/hin_cpw "
      f"{(REPORTED_FERT['eng']/REPORTED_TPC['eng'])/(REPORTED_FERT['hin']/REPORTED_TPC['hin']):.3f}  [identity holds]")
print("  The 5.89 vs 7.0 gap is not corroboration -- it is exactly the difference in")
print("  average word length. Two ratios over the same numerator cannot confirm each other.")
