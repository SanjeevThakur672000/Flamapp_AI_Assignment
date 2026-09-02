#!/usr/bin/env python3
"""
factorise.py -- split each language's token premium into the part that is a
property of the TEXT and the part that is a property of the TOKENIZER.

    premium = tokens_L/sent  /  tokens_eng/sent
            = [ bytes_L/sent / bytes_eng/sent ]   <- script factor
            x [ tokens_L/byte / tokens_eng/byte ] <- tokenizer factor

The script factor is computed from the corpus alone, so it MUST come out
identical for every tokenizer. That invariance is the proof: whatever varies
across columns cannot be a property of the script.

Usage:  python factorise.py results.json
"""
import json, sys

data = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "results.json"))
toks = list(data)
langs = [l for l in data[toks[0]] if l != "eng"]

print("=== script factor (bytes per sentence, vs eng) -- must be INVARIANT ===")
print(f"{'lang':<6}" + "".join(f"{t.replace('hf:','')[:14]:>16}" for t in toks) + f"{'spread':>9}")
script = {}
for l in langs:
    vals = []
    for t in toks:
        d, e = data[t][l], data[t]["eng"]
        vals.append((d["byte"] / d["sent"]) / (e["byte"] / e["sent"]))
    script[l] = sum(vals) / len(vals)
    print(f"{l:<6}" + "".join(f"{v:>15.3f}x" for v in vals)
          + f"{max(vals)-min(vals):>9.4f}")

print("\n=== tokenizer factor (premium / script factor) -- the part that MOVES ===")
print(f"{'lang':<6}" + "".join(f"{t.replace('hf:','')[:14]:>16}" for t in toks) + f"{'range':>9}")
for l in langs:
    vals = [data[t][l]["premium"] / script[l] for t in toks]
    print(f"{l:<6}" + "".join(f"{v:>15.2f}x" for v in vals)
          + f"{max(vals)/min(vals):>8.1f}x")

print("\n=== byte-level fallback check: tok/byte ~ 1.0 means NO vocabulary coverage ===")
print(f"{'lang':<6}" + "".join(f"{t.replace('hf:','')[:14]:>16}" for t in toks))
for l in ["eng"] + langs:
    print(f"{l:<6}" + "".join(f"{data[t][l]['tokens']/data[t][l]['byte']:>16.3f}" for t in toks))
print("\ngpt2 emits ~1 token per UTF-8 byte for the Dravidian languages: its BPE")
print("has essentially no merges for those scripts, so it degenerates to byte")
print("encoding. That is a fact about the vocabulary, not about the language.")

print("\n=== cost of switching, in tokens per sentence ===")
print(f"{'tokenizer':<26}{'eng':>9}{'hin':>9}{'tam':>9}{'eng penalty':>14}")
base = data[toks[0]]
for t in toks:
    d = data[t]
    pen = (d["eng"]["tokens"] / d["eng"]["sent"]) / (base["eng"]["tokens"] / base["eng"]["sent"])
    row = f"{t.replace('hf:',''):<26}"
    for l in ("eng", "hin", "tam"):
        row += f"{d[l]['tokens']/d[l]['sent']:>9.1f}" if l in d else f"{'-':>9}"
    print(row + f"{100*(pen-1):>+13.1f}%")
