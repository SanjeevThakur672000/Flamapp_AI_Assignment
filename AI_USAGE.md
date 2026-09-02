# AI_USAGE.md

Claude (Opus) was used throughout, as the brief permits. Summary of the split,
and of where it was wrong.

## What AI did

- Wrote every script in `partA/` and `partB/`, and the first drafts of
  `partA/AUDIT.md`, `partA/memo.md` and `partC/memo.md`.
- Proposed the central Part B hypothesis (that `reported_tok_s` counts prefill
  tokens) and the decode roofline model.
- Proposed the parallel-sentence denominator as the answer to A3.

## What I did

- Ran everything myself and pasted raw output back at each step. Every number
  in the submission is one I have reproduced on my own machine.
- Flagged `line.lower()` as suspect on my own first read of `fertility.py`,
  before involving AI. It became flaw F1 and measured +3.45%.
- Hand-verified the batch-24 row against the raw CSV independently of the
  script (Session 2): derived 1607.325 vs logged 1607.4.

## Where AI was wrong, and how it surfaced

**1. The NFC claim (retracted).** Claude verified `unicodedata.normalize("NFC")`
on the 10-line sample corpus, measured 0 of 20 lines changed, and filed it as
a "looks suspicious but is fine" non-bug. Running the ablation on FLORES-200
(1012 sentences) gave **-0.11%** — small but not zero. The claim was withdrawn.
Submitting it would have cost -5 under the unverified-claim rule. Root cause:
generalising from a 20-line sample. `random.seed(1337)` is the harmless thing
and is the only knob measuring exactly 0.0000.

**2. A derived column that contradicted its own argument.** Claude's
`goodput.py` computed `decode_goodput = batch / ITL`, which printed **480.0
tok/s for batch 48** — the highest long-prompt figure in the table, on the
worst-performing row. That undercut the B2 argument it was meant to support.
The formula assumes the submitted batch is resident; `preempted_seqs = 23`
disproves it. Corrected to 253.5 and 258.0.

**3. A near-miss over-claim.** Claude presented the 0.0000 spread in the
script factor as strong evidence that the token premium is tokenizer-driven.
It is **true by construction** — bytes per sentence is computed from the
corpus and cannot vary with the tokenizer. It is a pipeline check, not a
finding. Caught before submission and rewritten; the defensible version is
that the premium varies up to 14.7x while the script contribution is fixed,
and the `tok/byte` column (gpt2 at 0.997 for Tamil) is the direct evidence.

**Attribution note:** in all three cases Claude produced the error and Claude
also flagged it, in each case after I ran the experiment on real data and
pasted the output back. I did not independently catch any of the three. What
the process caught them with was running everything on a real corpus rather
than the sample, and checking each output against the argument it was
supposed to support.

## What I understand well enough to defend

- Why KV cache is 114,688 B/token and not 344,064 (GQA: 8 KV heads, not 24
  query heads).
- Why `reported_tok_s` inflates long-prompt rows, and why output goodput
  inverts the report's conclusion.
- Why `batch / ITL` breaks above batch 24.
- Why a whitespace word is the wrong denominator across languages, and why a
  parallel sentence is the only one that holds meaning constant.
- Why `tok/byte` near 1.0 indicates absent vocabulary coverage.

## What I would be slower on

- `I would be slower at **reproducing the roofline inversion that gives 26.4 resident sequences at batch 48**, since it requires carefully reconstructing the underlying assumptions, hardware constraints, and calculations rather than just recalling a reported figure.
`
