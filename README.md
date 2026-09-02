# Audit submission

```
partA/  build_corpus.py      A1  FLORES-200 -> corpus/  (asserts line alignment)
        corpus_facts.py      A2  word-count bug, denominator table, alignment check
        decompose.py         A2  refutes REPORT_v0 findings 2 and 3 with no tokenizer
        ablate.py            A2  one knob per claimed flaw, before/after on the ratio
        fertility_fixed.py   A3  multi-tokenizer x multi-denominator, token premium
        AUDIT.md             A2  findings, each tagged PROVEN or PENDING
        memo.md              A4  skeleton
partB/  reconcile.py         B3  identifies what reported_tok_s counts
        capacity.py          B1  KV arithmetic + roofline model
        goodput.py           B3  honest goodput, equal-footing, B2 fix estimate
        ANSWERS.md           B1-B4
partC/  memo.md              C
```

## Reproduce

See RUN.md for the full runbook.

```bash
pip install regex tiktoken transformers

# Part B — no network needed, runs against the provided log
python partB/reconcile.py && python partB/capacity.py && python partB/goodput.py

# Part A — tokenizer-free evidence
python partA/corpus_facts.py
python partA/decompose.py

# Part A — needs network
python partA/build_corpus.py --out corpus/
python partA/ablate.py --corpus corpus/ --tokenizer gpt2
python partA/fertility_fixed.py --corpus corpus/ \
    --tokenizer gpt2 --tokenizer cl100k_base --tokenizer o200k_base \
    --tokenizer hf:xlm-roberta-base --tokenizer hf:google/muril-base-cased
```

## Status

Part B is complete and every number reproduces from the scripts.
Part A's tokenizer-free claims are complete; claims tagged PENDING in
partA/AUDIT.md still need their measurement run and must not be submitted as
claims until they have one.
