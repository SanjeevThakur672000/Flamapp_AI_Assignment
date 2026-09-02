# How to run this

## 0. Layout

Put the submission next to the unzipped starter kit. All scripts default to
this layout; every one also takes an explicit path as argv[1] if yours differs.

```
audit/
├── starter_kit/          # unzipped as given
│   ├── fertility.py
│   ├── REPORT_v0.md
│   ├── bench/bench_log.csv
│   └── corpus_sample/
└── submission/           # this repo
    ├── partA/ partB/ partC/
    └── NOTEBOOK.md  AI_USAGE.md
```

## 1. Environment

```bash
cd audit/submission
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install regex                       # tier 1+2, no network at runtime
pip install tiktoken                    # tier 3
pip install transformers sentencepiece  # tier 3, MuRIL/XLM-R need sentencepiece
```

Python 3.9+. Record the versions in NOTEBOOK.md — the defense may ask why a
number moved.

## 2. Tier 1 — Part B (offline, ~1 second, run this first)

```bash
python partB/reconcile.py
python partB/capacity.py
python partB/goodput.py
```

Check against partB/ANSWERS.md before moving on:

| script | the number to confirm |
|---|---|
| reconcile | `err%` column ≤ 0.022 on all 13 rows |
| capacity  | 114,688 B/token; `floor(25.72) = 25`; `b-preempted = 25` at both b32 and b48 |
| goodput   | b24 long row: 200.9 e2e / 249.8 decode; batch-16 equal-footing −44% |

If those match, Part B is done and defensible.

## 3. Tier 2 — Part A, tokenizer-free (offline, ~1 second)

```bash
python partA/corpus_facts.py
python partA/decompose.py
```

Confirm: split inflation +1.28% / +1.64%; Hindi 4.75 cp/word vs English 5.74;
factors 2.181x script and 2.690x tokenizer, product 5.866.

## 4. Tier 3 — Part A, needs network

```bash
python partA/build_corpus.py --out corpus/        # ~500 MB tarball, few minutes
```

Must end with `[+] 8 languages, N aligned sentences each`. If the assert
fires, stop — the corpus is not parallel and nothing downstream is valid.
If dl.fbaipublicfiles.com is unreachable, fall back to
`pip install datasets` + `openlanguagedata/flores_plus` on HuggingFace and
write the same one-file-per-language layout.

```bash
python partA/ablate.py --corpus corpus/ --tokenizer gpt2
```

Fills the PENDING claims in AUDIT.md. Read the `d%` column: F1 (lowercasing)
and F4 (macro-average) are the two you must measure before claiming them.
A row at exactly 0.00% is a non-bug — record it as such, don't hide it.

```bash
python partA/fertility_fixed.py --corpus corpus/ \
    --tokenizer gpt2 --tokenizer cl100k_base --tokenizer o200k_base \
    --tokenizer hf:xlm-roberta-base --tokenizer hf:google/muril-base-cased \
    --json results.json
```

The final table is the A3/A4 answer. First run downloads ~2 GB of tokenizer
files; later runs are cached. Drop a `--tokenizer` if one is gated or slow —
gpt2 plus one Indic-aware model satisfies the brief's minimum.

## 5. Sanity check on the original

Run the intern's script yourself so you can reproduce its output in the
defense, and so you know the fixed script's delta is real:

```bash
cd ../starter_kit
python fertility.py --corpus eng=corpus_sample/eng_sample.txt \
                    --corpus hin=corpus_sample/hin_sample.txt --tokenizer gpt2
```

Compare against the table in REPORT_v0.md section 1. If it does not reproduce
1.27 / 7.45, that is itself a finding — log it.

## 6. Trouble

- `bench_log.csv not found` — pass the path: `python partB/reconcile.py /path/to/bench_log.csv`
- `pip install regex` fails — you need it for grapheme clusters; the stdlib has no equivalent.
- `mock` tokenizer in ablate.py is a plumbing self-test only. Never quote its numbers.
