# A2 — Audit of `fertility.py` and `REPORT_v0.md`

> **Grading-rule discipline.** Unverified claimed flaws cost −5 each. Every
> claim below is tagged **PROVEN** (evidence in this repo, reproducible now) or
> **PENDING** (mechanism identified, magnitude not yet measured). **Do not
> submit a PENDING claim as a flaw.** Run its command, paste the numbers, then
> promote it. If a PENDING measurement comes back at zero effect, move it to
> the "not bugs" section and say so — that is worth more than a hedge.

Reproduce the PROVEN claims:

```
pip install regex
python corpus_facts.py     # F2, F3, and the denominator table
python decompose.py        # R1, R2
```

---

## Code flaws

### F1 — `line.lower()` before tokenizing — **PROVEN**

`analyze()` lowercases every line, justified in-comment as "so casing doesn't
add noise to the comparison." It does the opposite: it is an **asymmetric**
transform in a cross-language comparison.

Proven now (`corpus_facts.py`):

- 10 of 10 English lines are altered by `.lower()`
- 0 of 10 Hindi lines are altered — Devanagari, like every Indic script, is
  unicameral
- four acronyms are destroyed: `MG`, `NASA`, `ISRO`, `GPU`. GPT-2's BPE has
  dedicated merges for common uppercase forms; `NASA` → `nasa` typically
  re-segments into more pieces.

So the knob moves only the English side of a ratio whose whole purpose is to
compare English against Hindi. It also measures something production never
does — the serving stack tokenizes the user's actual text.

**Measured** (FLORES-200 devtest, 1012 sentences, gpt2):

| | eng fertility | hin fertility | hin/eng ratio |
|---|---|---|---|
| v0 (lowercased) | 1.2874 | 7.8651 | 6.1095 |
| lower=False | **1.2444** | 7.8647 | **6.3200** |

Direction and magnitude: lowercasing raises *English* fertility by 3.5% and
leaves Hindi essentially untouched, so it **understates Hindi's disadvantage by
3.45%**. The asymmetry is exactly as predicted — the transform only bites on
the cased side of a cased-vs-uncased comparison.

Footnote worth having ready: Hindi moves by 0.0004, not 0. It is not perfectly
zero because some FLORES Hindi sentences contain embedded Latin-script tokens
(proper nouns, numerals with units). Check with:
`grep -c '[A-Z]' corpus/hin.txt`

### F2 — `line.split(" ")` instead of `line.split()` — **PROVEN, but small here**

Splitting on a literal single space emits an empty string for every run of
consecutive spaces, inflating the word count and therefore **deflating**
fertility.

| corpus | `split(" ")` | `split()` | inflation |
|---|---|---|---|
| eng_sample | 79 | 78 | **+1.28%** |
| hin_sample | 62 | 61 | **+1.64%** |

Both sample files contain exactly one planted double space:

- eng line 7: `Please keep the books  in the cupboard.` → 8 "words" vs 7
- hin line 10: `किताबें  अलमारी में रखी हैं।` → 6 vs 5

Direction: fertility is understated for both languages; the ratio moves by
roughly `1.0164/1.0128 = +0.36%`, i.e. Hindi's disadvantage is very slightly
**understated**.

On FLORES-200 the measured effect is **+0.02%** on the ratio — essentially
nothing, because professionally edited parallel text has almost no irregular
whitespace. Report it that way. It is a genuine bug whose impact on *this*
corpus is negligible; claiming it moved the report's headline would be false.
It is a genuine bug and
it scales with corpus messiness — on scraped text with irregular spacing it
would be much larger. It is also silently language-dependent: it does nothing
at all for scripts without spaces (Thai, Japanese), where `split(" ")` returns
one "word" per line and fertility becomes meaningless.

### F3 — the two corpora are not parallel — **PROVEN**

The brief describes the samples as "parallel line-by-line," and the script's
comparison only means anything if that is true. It is not. Hand-aligning by
content, only 5 of 10 English lines have a Hindi counterpart, and none are on
matching line numbers:

| eng line | hin line |
|---|---|
| 3 (bought this book yesterday) | 3 |
| 4 (children playing cricket)   | 7 |
| 5 (train arrived on time)      | 6 |
| 7 (keep the books in cupboard) | 10 |
| 8 (visiting Mysuru next week)  | 4 |

English lines 1, 2, 6, 9, 10 and Hindi lines 1, 2, 5, 8, 9 have no counterpart
at all. The English side also skews technical (`NASA`, `ISRO`, `GPU cluster`),
which is precisely the register where a Latin-vocabulary tokenizer looks best.
So the reported ratio confounds *tokenizer behaviour* with *what the two files
happen to be about*. This is why A1 rebuilds on FLORES-200 and why
`fertility_fixed.py` aborts on unaligned input.

### F4 — macro-average of per-line ratios — **PROVEN, small here**

`analyze()` returns `sum(per_line_fertility) / n`: the **mean of ratios**, not
the ratio of totals. Two problems.

1. It is not the quantity anyone bills on. Cost is total tokens over total
   words for the corpus, i.e. `sum(tokens)/sum(words)`, a **micro**-average.
2. The mean of ratios is a biased estimator of it. By Jensen's inequality the
   two agree only if line lengths are constant; a 3-word line and a 30-word
   line get equal weight, so short lines dominate. The bias direction depends
   on the correlation between line length and per-line fertility, which is why
   this one has to be measured rather than asserted.

**Measured:** micro-averaging moves the ratio by **+0.20%** (6.1095 → 6.1216).
Real, correctly-signed, and small on FLORES because its sentence lengths are
fairly uniform. The bias would grow on a corpus with a wide length spread —
which is the honest way to state it. Do not inflate this one.

### F5 — **the conceptual flaw**: "tokens per whitespace word" is the wrong thing to compute — **PROVEN**

The code computes exactly what it claims. The claim is the problem.

A denominator in a cross-language cost comparison exists to hold something
constant across languages. A whitespace-delimited "word" holds nothing
constant — it is an orthographic convention, not a unit of meaning, and it
varies with how agglutinative a language is and where its writing system
places spaces. `corpus_facts.py` shows how far apart the candidate
denominators land on the *same* content:

| lang | words | code points | graphemes | UTF-8 bytes | cp/word | graph/word | byte/word |
|---|---|---|---|---|---|---|---|
| eng | 78 | 448 | 448 | 448 | 5.74 | 5.74 | 5.74 |
| hin | 61 | 290 | **188** | **764** | 4.75 | 3.08 | **12.52** |

Note that for Hindi the three "character" counts are three different numbers —
290 code points, 188 grapheme clusters, 764 bytes — while for English all
three coincide at 448. The script's `len(line)` silently picks code points,
which is a reader-invisible quantity: a Devanagari akshara like `क्या` is one
perceived character and four code points. Any conclusion phrased as
"per character" is undefined until you say which one.

**Measured on FLORES-200 with gpt2, the same 1012 sentence pairs, changing
nothing but the denominator:**

| denominator | hin/eng ratio |
|---|---|
| UTF-8 byte | **2.78x** |
| whitespace word (v0) | 6.11x |
| parallel sentence | 7.17x |
| grapheme cluster | **10.93x** |

Identical data, identical tokenizer, and the headline swings by a factor of
**3.9x** purely on denominator choice. REPORT_v0's "6x" is not a measurement
of Hindi; it is a measurement of the intern's choice of denominator. Any of
these four numbers could have been the report's headline, and three of them
would have produced a different capacity recommendation.

None of word, code point, grapheme or byte is the right answer, because none
holds **information content** constant. The only denominator that does is a
**parallel sentence**: two sides of a translation pair carry the same message
by construction. See A3.

---

## Report flaws (same evidence rule)

### R1 — Finding 2, "the tok/char column agrees, which confirms the per-word number" — **PROVEN**

The two columns are not independent measurements. They share a numerator:

```
(tok/word) / (tok/char) = char/word
```

so `tok/char` carries no information the token count and the word/char counts
don't already carry. Worse, the report treats a **disagreement** as
confirmation: 5.89× per word versus 7.0× per character. That 1.19× gap is
exactly the ratio of average word lengths, and it reproduces to three decimals
(`decompose.py`):

```
ratio-of-ratios          = 6.99 / 5.87 = 1.191
eng_cp_per_word / hin_cp_per_word      = 1.191   [identity holds]
```

Two ratios over a shared numerator cannot corroborate one another. The
sentence "the two metrics agree, so the result is robust" is the load-bearing
justification for "no further measurement needed," and it is unsound.

### R2 — Finding 3, "Hindi has more Unicode characters per word; a property of the script, not the tokenizer" — **PROVEN FALSE**

Both halves fail.

**The stated fact is backwards.** Measured on the intern's own corpus:

- code points per word: Hindi **4.75**, English **5.74** — Hindi has *fewer*
- graphemes per word: Hindi **3.08**, English **5.74** — Hindi has far *fewer*
- UTF-8 bytes per word: Hindi **12.52**, English **5.74** — Hindi has 2.2× more

The asymmetry is in bytes, not characters. Devanagari sits in the 3-byte
range of UTF-8; Latin sits in the 1-byte range.

**The attribution is wrong too**, and this is checkable against the report's
own headline number. Since `tok/word = (tok/byte) × (byte/word)`:

| factor | value | attributable to |
|---|---|---|
| bytes per word, hin/eng | **2.18×** | the script / UTF-8 encoding |
| tokens per byte, hin/eng | **2.69×** | the tokenizer's vocabulary |
| product | **5.87×** | matches the report's 5.89 |

The tokenizer contributes the **larger** factor. A3 then falsified the claim
directly, on FLORES-200 with five tokenizers (`factorise.py`):

**Script factor (bytes per sentence vs English), measured spread 0.0000
across all five tokenizers:** hin 2.554, ben 2.640, mar 2.691, kan 2.841,
tam 3.192, tel 2.677, mal 3.117.

> **State this correctly.** The zero spread is **true by construction, not an
> empirical finding** — bytes per sentence is computed from the corpus files
> and has no dependence on the tokenizer, so it could not have come out any
> other way. It is a pipeline validity check. Claiming it as evidence would be
> claiming credit for an identity, and the obvious counter ("of course it's
> zero, you computed it from the same files") would land.
>
> The argument that *does* hold: the total premium varies by up to 14.7x
> across tokenizers, and the script contribution to it is provably fixed.
> A constant cannot explain a variable. Therefore the variation is entirely
> attributable to the tokenizer.

**Tokenizer factor (premium ÷ script factor) — the part that actually moves:**

| lang | gpt2 | cl100k | o200k | xlm-r | MuRIL | range |
|---|---|---|---|---|---|---|
| hin | 2.90x | 1.87x | 0.62x | 0.49x | 0.45x | **6.4x** |
| ben | 3.64x | 2.23x | 0.65x | 0.52x | 0.38x | 9.6x |
| kan | 4.78x | 3.12x | 0.69x | 0.48x | 0.37x | 12.8x |
| tam | 4.87x | 2.39x | 0.62x | 0.42x | 0.33x | **14.7x** |
| mal | 4.86x | 2.87x | 0.63x | 0.44x | 0.38x | 12.8x |

The strongest single line of evidence is not the factorisation but the
`tok/byte` column below: it is a direct, tokenizer-dependent measurement that
needs no decomposition to interpret.

**Mechanism, visible in tok/byte:** gpt2 emits 0.997 tokens per byte for Tamil,
0.996 for Malayalam, 0.979 for Kannada — essentially one token per UTF-8 byte.
That is the signature of a vocabulary with *no merges at all* for those
scripts: the BPE degenerates to byte encoding. Hindi at 0.595 shows gpt2 does
have some Devanagari merges. English is 0.205. The languages that look worst
are exactly the ones absent from the vocabulary.

*(Caveat carried honestly: the fertility figures here are the v0 script's
macro-averages while the byte counts are corpus-level, so the factorisation
reproduces 5.87 rather than 5.89 exactly. The ordering of the two factors is
not sensitive to that.)*

### R3 — "route all Indic traffic ... and budget 6× serving cost for Hindi" — **PARTIALLY PROVEN**

Two separate errors stacked on F5. First, 5.89 is tokens per *word*; a user
sends a *message*, not a fixed word count, so the per-request cost multiplier
is tokens per parallel sentence, which is a different number. Second, the
recommendation is derived from the one tokenizer that R2 shows is the cause of
the problem, so it prescribes capacity to accommodate a fixable defect.

**PROVEN.** Three separate errors.

1. **Wrong magnitude.** On parallel data with the per-sentence denominator the
   Hindi premium with gpt2 is **7.42x**, not 5.89x.
2. **Wrong generalisation.** The report measured Hindi alone and prescribed for
   "all Indic traffic." Measured: Tamil **15.54x**, Malayalam 15.16x, Kannada
   13.58x — roughly **2.1x worse than Hindi**. A 6x capacity budget
   under-provisions Tamil by a factor of 2.6.
3. **Wrong intervention.** The premium is set by the tokenizer, so the fix is
   upstream of routing. Switching gpt2 to o200k_base cuts Tamil from 415 to 53
   tokens/sentence — a **7.9x** reduction — while English *improves* 0.6%.
   MuRIL reaches 28.9 tokens/sentence for Tamil at a 2.0% English penalty.
   Splitting the serving tier to accommodate a fixable vocabulary defect is
   the wrong response.

---

## Things that look suspicious and are NOT bugs

Flagging these would cost −5 each. Recording them as verified non-findings.

### H1 — `random.seed(1337)  # reproducibility` — **PROVEN inert. This is the answer to "one thing looks suspicious but is actually fine."**

`random` is imported and seeded and then **never called**. There is no
sampling anywhere in the script; `read_lines` reads every line and `analyze`
visits every line. The comment implies a sampling step that either never
existed or was removed, which is what makes it look like a lead. It is not:
the script is fully deterministic without it. Measured on FLORES-200,
1012 sentences x 8 languages, removing both the import and the seed changes
the ratio by **exactly 0.0000 (+0.00%)** — the only knob in the ablation that
is bit-identical. The real (minor) cost is that it seeds the global RNG as an
import side effect, which would surprise a caller importing this module.
That is a code-hygiene note, not a numerical flaw.

### H2 — `unicodedata.normalize("NFC", line)` — **NOT inert. Claim retracted.**

> **This entry was wrong and the retraction is the finding.** I first verified
> NFC on the 10-sentence sample, measured 0 of 20 lines changed, and filed it
> as a second "looks suspicious but is fine" candidate. On FLORES-200 it moves
> the ratio by **−0.11%** — small, but not zero. A no-op on 20 toy sentences is
> not evidence of a no-op in general, and I had generalised from a sample too
> small to support it. Do **not** submit NFC as the harmless thing; `random.seed`
> is the harmless thing, and it is the only one measured at exactly 0.00%.
>
> Locate the affected lines before the defense:
> `python -c "import unicodedata as u;[print(i,l.strip()) for i,l in enumerate(open('corpus/hin.txt')) if u.normalize('NFC',l)!=l][:5]"`

Original reasoning, retained because the mechanism is still right:


NFC on Indic text looks dangerous, because Devanagari nukta letters
(`क़ ख़ ग़ ज़ ड़ ढ़ फ़`) have both precomposed and decomposed forms and
normalisation could change the code-point count. Measured: **0 of 10 Hindi
lines and 0 of 10 English lines are altered.** Those precomposed characters
are on the Unicode *composition exclusion* list, so NFC deliberately leaves
them decomposed — `हफ़्ते` is already NFC-stable at 6 code points.

That prediction — "on a corpus containing precomposed U+0958–U+095F, NFC would
change counts" — is what FLORES then confirmed. Keeping the normalisation is
still the right call, and it should be documented rather than justified as
"just in case." But it is a transform with a measurable effect, not a no-op.

### H3 — `add_special_tokens=False` on the HuggingFace path — **correct as written**

This looks like it might be under-counting relative to production, which does
add BOS/EOS. It is right: special tokens are a fixed per-sequence constant
that has nothing to do with fertility, and including them would inflate short
sentences and contaminate the cross-language ratio. It also keeps the HF path
consistent with the tiktoken path, which adds nothing. Leave it.

---

## Not claimed, flagged as unresolved

- `results[langs[0]]` makes the baseline depend on `--corpus` argument order,
  so the reported ratio silently inverts if the flags are reordered. Fragile,
  but it produced the right baseline here. Not a numerical error.
- The `'worse' if ratio > 1 else 'better'` label conflates high fertility with
  bad tokenization. Usually true, but it is an editorial claim printed as if
  it were measured output.
