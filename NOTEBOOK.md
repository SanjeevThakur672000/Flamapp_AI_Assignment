# NOTEBOOK.md — chronological lab notebook

> Chronological log kept as the audit progressed. Attribution of who found
> what is stated inline; see AI_USAGE.md for the summary.

---

## Session 1 <2026-09-02 08:15> — orientation

Read the assignment brief through once, fairly quickly, then opened the
starter kit files directly — `fertility.py`, `REPORT_v0.md`, and the bench
CSV.

**First reaction on reading `fertility.py`: the `line.lower()` looked wrong.**
No measurement behind that yet, just that lowercasing before tokenizing seemed
like it was throwing away information the tokenizer is supposed to see. Logged
it as my first hypothesis to test.

Nothing else jumped out on a first read. I did not have a hypothesis about the
denominator, the averaging, or the bench log at this point.

**Decision:** hand the harness-building to Claude, since the brief states AI
use is expected. Working rule for the rest of the audit: Claude proposes and
writes, I run everything myself and check each number against the source data
rather than accepting output.

> Following this thread: the lowercasing hunch was confirmed in Session 7 at
> **+3.45%**, and the direction turned out to be the opposite of what I
> assumed — it inflates *English* fertility, so v0 **understates** Hindi's
> disadvantage rather than exaggerating it.

---

## Session 2 <2026-09-02 08:24> — Part B: what does `reported_tok_s` measure?

**Hypothesis** (Claude's, which I then tested): the counter includes prefill
tokens, i.e. `num_requests x (prompt_len + gen_len) / wall_clock_s`.

**Ran:** `python partB/reconcile.py`

**Result:** matched on all 13 rows, max error 0.022%. Fit that tight across
rows spanning 70 to 2267 tok/s is not coincidence.

**Consequence:** both REPORT_v0 Section 2 conclusions collapse. On equal
footing (same batch, output tokens only) long prompts are 19-65% *worse*,
not better. And batch 48 reads 1298.5 in the log the report itself cites —
below batch 24's 1607.4 — so the "~3200 tok/s" extrapolation runs past a
measured point that contradicts it.

**Process note, honestly:** I did not hand-verify any individual row against
the CSV at this point — I took the table as printed. The fit across 13 rows
was tight enough that I accepted it.

**Closed at 12:40.** Hand-checked the batch-24 long-prompt row directly
against the raw CSV, independently of my own code:

```
$ python -c "print(24*(3584+512)/61.16)"
1607.3250490516677
$ grep '^24,' ../starter_kit/bench/bench_log.csv
24,3584,512,24,61.16,1607.4,500.5,96.07,69221.3,0,0.93
```

Derived 1607.325 against a logged 1607.4 — agreement to the log's
one-decimal rounding. The counter identity holds without the script.

---

## Session 3 <2026-09-02 08:48> — Part B: capacity

**Hypothesis:** KV cache is the binding constraint, and the ceiling is
computable from the spec alone.

**Ran:** `python partB/capacity.py`

**Result:** 114,688 B/token (GQA — 8 KV heads, not the 24 query heads).
Predicted 25 sequences on decimal GB, 28 on binary GiB. Log gives 25.8 from
`kv_util / batch`, and `batch - preempted = 25` at both batch 32 and 48.
Three independent confirmations, and the decimal reading wins.

**On the GB vs GiB ambiguity:** I expected the decimal reading (25) to be the
right one, and the log then agreed — `kv_util / batch` gives 25.8 against a
predicted 25.72. The retrospective justification is that GPU vendor specs
quote capacity in decimal GB, so "24 GB" in `model_spec.md` most likely means
24e9 bytes. I did not have that argument in hand when I picked it; the
agreement with the log is what actually settled it, and either way the
conclusion is unchanged at the level that matters — capacity is ~25-26, not
~32 or ~48.

---

## Session 4 <2026-09-02 09:37> — DEAD END: the goodput column contradicted its own argument

**Observed:** `decode_goodput` printed **480.0 tok/s** for batch 48 — the
highest long-prompt value in the table, on the row with the *worst* real
performance. It directly contradicted the B2 argument it was meant to support.

**Diagnosis:** the column computed `batch / ITL`, which assumes the submitted
batch is actually resident. `preempted_seqs = 23` disproves that. Above batch
24 the running batch is capped near 25.8, so the formula over-counts.

**Revision:** clamp to the capacity estimate on preempted rows and flag them.
Corrected values 253.5 (b32) and 258.0 (b48).

**Lesson:** a derived column that flatters the wrong conclusion is a bug, not
a finding. Had I pasted the original table into the submission it would have
been evidence against my own argument.

**Attribution, plainly:** I did not spot this. Claude wrote the script,
Claude noticed the contradiction when I pasted my output back, and Claude
proposed the fix. What I did was run it and follow the reasoning once
`preempted_seqs` was pointed at — the column assumes the submitted batch is
resident, and the log says 23 of 48 were preempted, so it cannot be.

---

## Interlude <2026-09-02 09:55> — lost the starter kit

Cleaning up a duplicated `starter_kit/starter_kit/` nesting from the zip, I
ran an `mv` that had already been applied and then `rm -rf`'d the parent.
Scripts started failing with `bench_log.csv not found`. Recovered it from
`~/.local/share/Trash/files/` with `cp` rather than `mv`, so the trash copy
stayed as a backup. Also added a `.gitignore` for `.venv/` and `corpus/` at
this point so the submission zip would not carry the virtualenv.

No bearing on any result. Logged because it happened.

---

## Session 5 <2026-09-02 10:01> — Part A: tokenizer-free evidence

**Ran:** `partA/corpus_facts.py`, `partA/decompose.py`

**Result:** REPORT_v0's Finding 3 ("Hindi has more Unicode characters per
word") is false by its own data — Hindi is 4.75 cp/word vs English 5.74, and
3.08 graphemes vs 5.74. The asymmetry is bytes (12.52 vs 5.74). Finding 2 is
an independence fallacy: `(tok/word)/(tok/char) = char/word`, shared
numerator, and the ratio-of-ratios reproduces to 1.191 exactly.

Also: the two sample corpora are **not parallel**, despite the brief saying
so. Only 5 of 10 English lines have a Hindi counterpart, none on matching
line numbers.

**Most surprising to me:** that the two sample corpora are not parallel. The
assignment brief itself describes them as "parallel line-by-line," so I had
taken that as given. It means the intern's entire English-vs-Hindi comparison
was run across two files about different things — the ratio confounds
tokenizer behaviour with subject matter. It also explains why rebuilding on
genuinely aligned data (FLORES) was worth the effort rather than just fixing
the script.

---

## Session 6 <2026-09-02 10:25> — DEAD END: the NFC claim was retracted

**Initial claim** (from the sample corpus): `unicodedata.normalize("NFC")`
is inert — 0 of 20 lines changed — so it is a second "looks suspicious but is
fine" candidate, alongside `random.seed`.

**Ran:** `partA/ablate.py` on FLORES-200, 1012 sentences.

**Result:** NFC moves the ratio by **-0.11%**. Small, but not zero.

**Revision:** claim retracted. A no-op on 20 toy sentences is not evidence of
a no-op in general — the sample was too small to support the generalisation.
`random.seed(1337)` is the harmless thing, and it is the only knob measured at
**exactly 0.0000**. Submitting NFC as a non-bug would have cost -5.

**Attribution:** the original NFC claim was Claude's, made from the 10-line
sample corpus, and Claude retracted it once I ran the ablation on FLORES and
pasted the -0.11% back. I did not catch it independently — what I did was run
the experiment on real data, which is what exposed it.

The transferable lesson, and the reason this entry matters more than the
result: the sample corpus is 20 lines and cannot support a claim about
Unicode normalisation in general. Every conclusion drawn from
`corpus_sample/` needed re-checking on FLORES before it went in the audit.

---

## Session 7 <2026-09-02 10:49> — Part A: the ablation

**Ran:** `python partA/ablate.py --corpus corpus/ --tokenizer gpt2`

**Results** (v0 baseline ratio 6.1095):

| knob | effect on ratio |
|---|---|
| F1 lowercasing | **+3.45%** — inflates *English*, so v0 understates Hindi |
| F2 `split(" ")` | +0.02% — real bug, negligible on clean text |
| F4 macro-average | +0.20% — real, small, uniform sentence lengths |
| denominator: byte / word / sentence / grapheme | **2.78x / 6.11x / 7.17x / 10.93x** |

**The finding:** identical data, identical tokenizer, and the headline swings
**3.9x** on denominator choice alone. REPORT_v0's "6x" measures the intern's
choice of denominator, not Hindi.

**On keeping F2 and F4 despite their size:** both are genuine defects —
`split(" ")` miscounts words and the macro-average is the wrong estimator —
and both are reported at exactly the magnitude measured, +0.02% and +0.20%.
The scoring rule penalises unverified claims, not small ones. Reporting a real
bug at its true negligible size is the correct outcome; inflating either into
"this moved the headline" would have been false. The honest statement is that
they are bugs whose impact on *this* corpus is near zero, and that F2 in
particular would grow on scraped text with irregular whitespace.

---

## Session 8 <2026-09-02 11:03> — Part A: five tokenizers

**Ran:** `partA/fertility_fixed.py`, then `partA/factorise.py`

**Result:** Hindi premium **7.42x (gpt2) -> 1.16x (MuRIL)**. Tamil
**15.54x -> 1.06x**. gpt2 emits 0.997 tok/byte for Tamil, 0.996 Malayalam,
0.979 Kannada — one token per UTF-8 byte, the signature of a vocabulary with
no merges for those scripts at all.

**Consequence:** "a property of the script, not the tokenizer" is refuted.
Also: the report measured Hindi alone and prescribed for all Indic. Tamil is
2.1x worse than Hindi, so a 6x budget under-provisions it by 2.6x.

MuRIL reaches Tamil 28.9 tok/sentence (from 415.2) for a +2.0% English
penalty; xlm-roberta gets similar Indic numbers but costs English 13.4%.

---

## Session 9 <2026-09-02 11:13> — DEAD END: the 0.0000 invariance, nearly over-claimed

**Observed:** the script factor came out with spread **0.0000** across all
five tokenizers. Looked like a striking empirical confirmation.

**Revision:** it is **true by construction**. Bytes per sentence is computed
from the corpus files and has no dependence on the tokenizer — it could not
have come out otherwise. It is a pipeline validity check, not evidence.

**What I claim instead:** the premium varies up to 14.7x while the script
contribution is provably fixed; a constant cannot explain a variable. The
`tok/byte` column is the stronger evidence because it is a direct
tokenizer-dependent measurement needing no decomposition.

**Attribution:** Claude produced the 0.0000 spread, presented it as strong
evidence, and then flagged its own over-claim before I submitted anything. I
did not catch it. Recording it because it is the clearest example in this
audit of the failure mode the brief warns about — a number that looks like
confirmation but is an identity, and would have been dismantled in one
sentence during the defense.

---

## Still open / would do with more time

- `e2e_ms_p95` exceeds `wall_clock_s` in 12 of 13 rows by 9-18%, which is odd
  if requests are simultaneous. Batch 48 is the exception (ratio 0.696) and is
  consistent with a preemption long tail. No claim rests on this column.
- FLORES is formal Wikipedia prose. Production traffic is code-mixed and
  romanised; romanised Hindi would tokenize near 1.0x. Unmeasured.
- Did not verify that MuRIL's premium survives on conversational text.
- Total effort: **~7 hours** — ~4.5 h of logged work in the sessions above,
  plus ~2.5 h reading the brief, environment setup, and re-running scripts
  after each correction. Against the brief's ~10-hour budget. I stopped
  at the point where every claim had a measurement behind it rather than
  extending coverage, on the brief's own guidance that a sharp short
  submission beats a bloated long one.
