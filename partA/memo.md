# A4 — Recommendation memo

**Corpus:** FLORES-200 devtest, 1012 parallel sentences x 8 languages
(tarball sha256 `b8b0b767...`). **Metric:** token premium — total tokens for
language L over total tokens for English on the *same* sentences.

## Corrected headline numbers

| language | gpt2 | cl100k_base | o200k_base | xlm-roberta | MuRIL |
|---|---|---|---|---|---|
| hin | **7.42x** | 4.77x | 1.57x | 1.25x | 1.16x |
| ben | 9.61x | 5.88x | 1.71x | 1.37x | 1.00x |
| mar | 7.86x | 5.05x | 1.82x | 1.22x | 1.06x |
| kan | 13.58x | 8.86x | 1.97x | 1.35x | 1.07x |
| tam | **15.54x** | 7.64x | 1.98x | 1.35x | 1.06x |
| tel | 12.97x | 8.29x | 1.93x | 1.32x | 1.20x |
| mal | 15.16x | 8.94x | 1.96x | 1.38x | 1.18x |

REPORT_v0 said 5.89x for Hindi and generalised it to all Indic traffic. Both
halves are wrong: Hindi is 7.42x on the correct denominator, and Tamil is
15.54x — 2.1x worse than the language actually measured.

## Routing recommendation

**Do not split the serving tier, and do not budget 6x. Change the tokenizer.**

The premium factors into a script term (bytes per sentence) and a tokenizer
term. The script term is invariant across all five tokenizers to within 1% —
2.56x for Hindi, 3.19x for Tamil. The tokenizer term spans **6.4x for Hindi
and 14.7x for Tamil**. Almost all of the cost is vocabulary coverage, and gpt2
emits ~1.0 tokens per UTF-8 byte for Tamil, Malayalam and Kannada, which is
the signature of a BPE with no merges for those scripts at all.

Moving to an o200k-class tokenizer takes Tamil from 415 to 53 tokens/sentence
(7.9x cheaper) while English gets 0.6% *better*. This matters directly for
capacity: from Part B, KV cache binds at ~25 concurrent 4096-token sequences.
Under gpt2 a 4096-token budget holds ~10 Tamil sentences against ~153 English;
under o200k it holds ~78. The report's proposed separate Indic tier would be
provisioning hardware around a defect that costs nothing to fix at model
selection time.

**Caveat on the intervention:** a tokenizer cannot be hot-swapped into a
deployed decoder — the embedding matrix is tied to the vocabulary, so this is
a constraint on *model choice*, not a config change. For the current stack the
actionable step is to budget from the measured per-language premium of the
tokenizer we actually serve, not from a single Hindi number.

## Biggest caveat

FLORES-200 is professionally translated, formal, Wikipedia-register prose.
Production traffic is none of those: it is conversational, short-turn,
code-mixed, and heavily **romanised** — Hinglish and Kanglish written in Latin
script. Romanised Hindi tokenizes almost like English and would show a premium
near 1.0x. **The true production premium is therefore likely well below every
number above, by an amount set by our romanisation rate, which we have not
measured.** These figures bound the worst case for native-script formal text;
they are not an estimate of our bill. The corpus is also single-domain and
speaks only to input tokens, while decode cost is driven by output.

## The one metric to monitor in production

**Tokens per completed conversation turn, by language, as a ratio to English —
p50 and p95, on live traffic.**

It is the same quantity this memo estimates, measured on the real domain, the
real length distribution and the real script mix, and it covers output tokens
as well as input. Divergence from the offline prediction falsifies the
analysis, and the direction identifies the cause: lower means we mispredicted
register or romanisation rate; higher means production text is worse for the
tokenizer than FLORES prose, which is the case that costs money. p95 matters
separately because capacity is set by the tail — a language whose p95 turn is
3x English exhausts the KV cache 3x faster regardless of the median.
