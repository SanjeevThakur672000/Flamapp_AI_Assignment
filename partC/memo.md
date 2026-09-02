# Part C — Casual-register Indic outputs: recommendation

**Recommendation: ship path (c), prompt engineering, as the 3-week launch
path. Run path (a) as a Hindi+Kannada-only LoRA track behind it, on data that
(c) generates — and do not let it gate the launch. Reject path (b).**

## Assumptions (stated so they can be attacked)

1. The base model is an instruction-tuned dense model in the 7–8B class,
   served as in Part B. Path (a) means LoRA, not full fine-tuning.
2. "No external API budget" means no frontier-model access for generating
   synthetic casualization pairs. This is the binding constraint on (a), not
   compute.
3. The reviewer covers Hindi and Kannada only. Bengali, Marathi, Tamil and
   Telugu **cannot be validated at all** in this window, whichever path wins.
4. Register (formal vs casual) is a style axis the base model already spans in
   these languages and needs steering toward, not a capability it lacks. If
   this is false, (c) fails and the kill criterion fires — see below.
5. Reviewer throughput: ~50 short-response judgements/hour on a blind pairwise
   comparison, i.e. ~500 judgements/week, ~1,500 total.

## Back-of-envelope arithmetic

**Compute is not the constraint.** LoRA SFT on 6 languages x 3,000 pairs x
~400 tokens = 7.2M tokens. At `6 x 7e9 x 7.2e6 = 3.0e17` FLOPs/epoch and
~125 TFLOPS effective (A100-80GB bf16 at ~40% MFU), that is **~40 min/epoch**,
~2 GPU-hours for 3 epochs. Self-distilling 30k responses at ~300 output tokens
adds ~1.5 GPU-hours. Total ~6 hours against a **336 GPU-hour** budget: 2%.

**Evaluation is the constraint.** 3 weeks x 10 h = **30 reviewer-hours ≈ 1,500
judgements, across 2 of 6 languages**. One properly powered A/B round is
n=200 pairs x 2 languages = 400 judgements. That buys **three rounds, total**,
and only if none are wasted. Every design decision below follows from this
number, not from the GPU.

**Serving cost, path (b).** A 1B rewriter is a second full decode pass over
every response. From Part B, decode is memory-bandwidth bound: adding ~2 GB of
weights to stream per step, plus a second KV cache, plus re-generating every
output token. Realistically **1.6–2x output-token cost and +40–100% p50
latency**, on a box already shown to saturate at ~25 concurrent long-context
sequences. Path (b) spends the scarcest serving resource to solve a style
problem.

**Prompt-token cost, path (c).** Few-shot casual exemplars ride on every
request. Ten short exemplars ≈ 400 English-equivalent tokens, but per Part A
these are Indic-script tokens: with a non-Indic-aware tokenizer that is a
~2–6x multiplier, so **~1,000–2,400 extra prompt tokens per request**. At
3,584-token prompts this is a 30–60% prefill increase. Real, but prefill is
compute-bound and cheap relative to decode, and it can be cut by moving the
exemplars into a cached system prefix.

## Why (c), and why not the others

Path (a) at 6 languages is unfundable as specified: with no external API
budget, the only source of "casualized" pairs is the model that is already too
formal. Bootstrapping casual style out of a formal model is the whole problem,
not a preprocessing step. Path (b) doubles serving cost, adds a second failure
mode (a rewriter that alters meaning, not just register), and still needs the
same training data that (a) can't get.

Path (c) is the only option that is **reversible in one deploy**. Since four of
six languages ship unvalidated no matter what, reversibility is the dominant
consideration: an unvalidated prompt regression is rolled back in minutes; an
unvalidated weight change ships a subtly broken Tamil assistant and we find out
from users.

The non-obvious payoff: **(c) is the data engine for (a).** Once a prompt
reliably produces casual output, use it as a teacher to self-distil 5k pairs
per language, filter, and LoRA-train on that. (a) becomes reachable without
any external API — but as a week-4+ project that removes the prompt overhead,
not as a launch dependency.

## Success metric and threshold

**Primary:** blind pairwise preference, baseline vs candidate, on 200 sampled
real production prompts per language, Hindi and Kannada. Reviewer sees two
unlabelled responses and picks the one a friend would actually say.

**Threshold to ship: ≥65% preference for the candidate, with the lower bound
of the 95% CI above 55%.** At n=200 and p=0.65 the standard error is 3.4%, so
the CI is roughly ±6.6% and a 65% point estimate clears 55% with margin. A
50% result is the null; 55–60% is a real but too-small effect to justify the
prompt-token cost.

**Guardrail (must also pass):** semantic-preservation regression ≤2% on the
same sample — the casual response must not drop content the formal one had.
Casual and wrong is worse than formal and right.

**Proxy for the four unvalidated languages:** automated register signals
(honorific-form rate, mean sentence length, code-mixing rate) must move in the
same direction and within 1.5x the magnitude seen in Hindi/Kannada. This does
not prove quality; it catches the case where the prompt does something wildly
different in Tamil.

## Kill criterion

**If, by end of week 2 (after two prompt iterations), Hindi preference is
below 55% or the 95% CI lower bound is below 50%, abandon (c) as the launch
path.** Two failed iterations against a 30-hour reviewer budget means the
remaining 10 hours cannot produce a validated result, and assumption 4 is
probably wrong — the base model does not have the casual register available in
these languages and no prompt will find it.

Fallback at that point is **no ship**: go to the launch review with the
baseline formality measurements, the two failed iterations, and a request for
either native-speaker data collection or reviewer coverage for the remaining
four languages. Shipping an unvalidated style change to six languages to hit a
date is the failure mode this criterion exists to prevent.

Secondary kill, for the (a) track: if self-distilled LoRA does not beat the
prompt-only candidate by ≥5 points on the same metric by end of week 4, drop
it and keep the prompt.

## Day-1 experiment

**Build the measurement instrument and the baseline — not the model.**

Sample 200 real production prompts per language for Hindi and Kannada. Generate
current responses. Have the reviewer rate formality 1–5 and answer "would a
friend say this?" — ~2 reviewer-hours for 400 items. Include **20 duplicated
items** to measure intra-rater consistency.

This is day 1 because three things have to be true before any modelling is
worth doing, and none of them is currently established:

1. **The problem is real and sized.** "Too formal" is a product complaint. If
   the baseline scores 4.2/5 formal in Hindi but 2.8 in Kannada, this is one
   language's problem and the whole plan changes.
2. **The instrument works.** If the reviewer disagrees with themselves on the
   duplicated items more than ~15% of the time, the 65% threshold is
   unmeasurable and the rubric needs rewriting before it burns the budget.
3. **There is a before.** Without a baseline the week-3 A/B has nothing to be
   an A/B against, and 30 irreplaceable reviewer-hours produce an unfalsifiable
   result.

Two hours spent here protects the other twenty-eight.
