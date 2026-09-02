# Part B — Capacity reconciliation

All numbers reproduce with:

```
python reconcile.py    # B3: identifies what reported_tok_s actually counts
python capacity.py     # B1, B2 mechanism, roofline model
python goodput.py      # B3 goodput, equal-footing comparison, B2 fix estimate
```

---

## B1 (7 pts)

### (a) KV-cache bytes per token — exact

Per layer, per token we store one K vector and one V vector, sized by the
**KV** head count (GQA — 8), not the query head count (24):

```
2 (K,V) x 8 kv_heads x 128 head_dim x 2 bytes (fp16) = 4,096 B per layer
x 28 layers                                          = 114,688 B per token
                                                     = 112 KiB/token
```

The 24 query heads are a decoy: with GQA they share the 8 KV heads. Using 24
would give 344,064 B/token, 3x too large.

### (b) Max concurrent 4096-token sequences

```
memory budget      24 GB x 0.92 gpu_memory_utilization = 22.08 GB
- weights          4.2e9 params x 2 B (fp16)           =  8.40 GB
- non-KV overhead  (given)                             =  1.60 GB
                                                        --------
= KV pool                                                12.08 GB

per sequence at max_model_len:  4096 x 114,688 B = 469.76 MB = 0.4698 GB

12.08 / 0.4698 = 25.72  ->  25 concurrent full-length sequences
```

Unit-convention sensitivity, stated honestly: if "24 GB" means 24 GiB and the
overhead is 1.6 GiB, the same arithmetic gives 12.66 GiB / 0.4375 GiB = 28.9,
i.e. 28 sequences. The prediction is therefore **25–28**, and the log
discriminates between them (below).

### Check against the log

`kv_cache_util` on the 3584-prompt rows, where every sequence reaches exactly
3584 + 512 = 4096 tokens, so utilisation is a direct read of capacity:

| batch | kv_cache_util | preempted | batch / util | batch − preempted |
|---|---|---|---|---|
| 4  | 0.16 | 0  | 25.0 | 4  |
| 8  | 0.31 | 0  | 25.8 | 8  |
| 16 | 0.62 | 0  | 25.8 | 16 |
| 24 | 0.93 | 0  | 25.8 | 24 |
| 32 | 0.97 | 7  | —    | **25** |
| 48 | 0.97 | 23 | —    | **25** |

Three independent confirmations of the same number:

1. Utilisation is exactly linear in batch at **0.03875 per sequence** →
   implied capacity **25.8**.
2. At batch 32, `32 − 7 preempted = 25`.
3. At batch 48, `48 − 23 preempted = 25`.

The measured 25.8 matches the decimal-GB arithmetic (25.72) to within 0.3%
and rules out the 28.9 GiB reading. **Capacity is ~25–26 concurrent
4096-token sequences.** The prediction was right; the log settles the unit
ambiguity in favour of decimal GB.

---

## B3 (4 pts) — do this before B2; it explains B2

*(Answering out of order because B2's anomaly is only visible once the column
is corrected.)*

### The misread column: `reported_tok_s`

It is not output throughput. Testing the hypothesis
`reported_tok_s = num_requests x (prompt_len + gen_len) / wall_clock_s`
against **all 13 rows** (`reconcile.py`) gives a maximum error of **0.022%**:

| batch | prompt | reported | predicted | err |
|---|---|---|---|---|
| 1  | 512  | 70.2   | 70.2   | +0.002% |
| 16 | 512  | 883.2  | 883.4  | +0.022% |
| 64 | 512  | 2267.3 | 2267.2 | −0.006% |
| 24 | 3584 | 1607.4 | 1607.3 | −0.005% |
| 48 | 3584 | 1298.5 | 1298.5 | +0.001% |

The counter credits **prefill tokens as throughput**. A 3584-token prompt
donates 3584 "free" tokens to the numerator, and prefill is a parallel,
compute-dense operation — cheap per token compared with decode, which emits
one token per sequence per step and is memory-bandwidth bound. Mixing them in
one counter makes long prompts look fast by construction. Both of the
report's Section 2 conclusions descend from this single conflation.

### Honest goodput of the batch-24 long-prompt row

**Way 1 — end-to-end, from wall clock:**

```
24 requests x 512 generated tokens = 12,288 output tokens
12,288 / 61.16 s = 200.9 output tok/s
```

**Way 2 — steady-state decode, from inter-token latency:**

```
24 sequences each emitting 1 token per itl_ms_p50 = 96.07 ms
24 / 0.09607 s = 249.8 output tok/s
```

The two differ by design, and the gap is itself checkable — it is prefill
amortisation:

```
decode phase  = 512 steps x 96.07 ms = 49.19 s
wall clock                           = 61.16 s
residual prefill                     = 11.97 s

prefill work  = 24 x 3584 = 86,016 tokens
              = 2 x 4.2e9 params x 86,016 = 7.23e14 FLOPs
at 121 TFLOPS peak                    = 5.97 s
implied MFU                           = 5.97 / 11.97 = 50%
```

50% model-FLOPs utilisation on prefill is entirely ordinary for a real
serving stack, so the two derivations are consistent rather than in conflict.
**Report ~201 output tok/s end-to-end; ~250 output tok/s in steady decode.**
Either is defensible; quoting 1607 is not.

### What the report should have said

**Claim 1 — "longer prompts give better throughput."** Sign-inverted. On
equal footing (same batch size, output tokens only):

| batch | short-prompt goodput | long-prompt goodput | true delta | what the counter said |
|---|---|---|---|---|
| 4  | 87.0  | 70.7  | **−19%** | +117% |
| 8  | 165.2 | 112.8 | **−32%** | +82%  |
| 16 | 294.5 | 163.9 | **−44%** | +48%  |
| 32 | 496.5 | 173.0 | **−65%** | −7%   |

Long prompts are 19–65% **worse** for user-visible output throughput at
matched batch size. They consume KV cache, which is the binding constraint,
and return nothing extra to the user.

**Claim 2 — "batch 48 should give ~3200 tok/s."** This extrapolates past a
measured point that contradicts it: the batch-48 row is *in the log the
report cites* and reads 1298.5 tok/s, which is lower than batch 24's 1607.4.
Throughput does not scale linearly with batch; it peaks at batch 24 and
declines. Honest output goodput at batch 48 is **162.3 tok/s**, worse than
batch 24's 200.9. (Also: "1600 tok/s (best observed)" is not the best
observed value even by the report's own counter — batch 64 short-prompt
reads 2267.3.)

**Corrected statement:** the harness counter measures total tokens processed,
not tokens delivered. On this GPU the box saturates at ~25 concurrent
4096-token sequences and peak user-visible goodput is ~200 output tok/s for
long-context traffic and ~756 output tok/s for 512-token prompts at batch 64.
Capacity planning should use output goodput at a fixed prompt-length mix.

---

## B2 (6 pts)

### The anomaly

In the 3584-prompt sweep, `reported_tok_s` rises 565 → 903 → 1311 → **1607**
(batch 4→24), then **falls** to 1384 (batch 32) and 1298 (batch 48).
Throughput is non-monotone in batch size, peaking at 24. Naive expectation is
sublinear but monotone increase. Output goodput shows the same turn:
200.9 (b24) → 173.0 (b32) → 162.3 (b48).

### Mechanism, by specific rows and columns

**KV-cache exhaustion at ~25 sequences, then preemption-and-recompute
thrashing.** Four columns line up:

1. `kv_cache_util` climbs linearly (0.16 / 0.31 / 0.62 / 0.93) and then
   **clamps at 0.97** for both batch 32 and batch 48. The pool is full.
2. `preempted_seqs` is 0 for every row through batch 24 and becomes non-zero
   (7, then 23) at **exactly** the batches where throughput turns over. In
   both cases `batch − preempted = 25` — the B1 capacity number.
3. `ttft_ms_p50` is flat at 483–500 ms for batches 4–24 and then jumps to
   636.9 (b32) and 955.4 (b48). Requests that cannot be admitted queue, and
   preempted sequences must re-run prefill over their whole 3584-token
   prompt — work already paid for once.
4. `itl_ms_p50` is the decisive column. It rises 51.3 → 62.3 → 77.2 → 96.1
   through batch 24, then **barely moves**: 101.8 at batch 32 and 100.0 at
   batch 48. If 48 sequences were genuinely decoding together, per-token
   latency would rise steeply. It does not, because the running batch is
   still ~25.

Point 4 is quantifiable. Decode is bandwidth-bound: each step must stream the
weights plus every resident sequence's KV cache. With mean context
3584 + 512/2 = 3840 tokens:

```
bytes/step = 8.40 GB (weights) + batch x 3840 x 114,688 B
ITL_roofline = bytes / 300 GB/s
```

| batch | GB/step | roofline ITL | observed ITL | MBU | seqs implied by ITL |
|---|---|---|---|---|---|
| 4  | 10.16 | 33.9 ms | 51.33  | 0.66 | 4.2  |
| 8  | 11.92 | 39.7 ms | 62.26  | 0.64 | 9.2  |
| 16 | 15.45 | 51.5 ms | 77.20  | 0.67 | 16.0 |
| 24 | 18.97 | 63.2 ms | 96.07  | 0.66 | 24.6 |
| 32 | 22.49 | 75.0 ms | 101.79 | 0.74 | **27.2** |
| 48 | 29.54 | 98.5 ms | 100.00 | 0.99 | **26.4** |

Memory-bandwidth utilisation is a stable 0.64–0.67 for batches 4–24. Holding
that efficiency fixed and inverting the model to solve for the *actual*
number of resident sequences gives 27.2 at batch 32 and 26.4 at batch 48 —
not 32 and 48. The apparent MBU jump to 0.99 is not the GPU getting more
efficient; it is the model being fed the wrong batch size. Independent
confirmation of the ~25–26 ceiling from B1.

So beyond batch 24 the extra requests buy nothing: they sit in the waiting
queue, and the ones that were admitted get evicted and re-prefilled. The
system does strictly more work for strictly less delivered output.

### Proposed change with predicted quantitative effect

**Set `max_num_seqs = 24` and let the scheduler queue the remainder.**

At an offered load of 48 concurrent long-context requests, the server runs
two clean waves of 24 instead of thrashing across 48:

| | observed (b48) | predicted with max_num_seqs=24 |
|---|---|---|
| wall clock | 151.41 s | 2 x 61.16 = **122.3 s** (−19.2%) |
| output goodput | 162.3 tok/s | **200.9 tok/s** (+23.8%) |
| `preempted_seqs` | 23 | **0** |
| `ttft_ms_p50`, wave 1 | 955.4 ms | **~500 ms** |

Wave-2 TTFT gets worse (it waits ~61 s), which is the honest trade: this
converts an invisible throughput collapse into visible, schedulable queueing.
If the TTFT tail is unacceptable, the capacity lever rather than the
admission lever is **fp8 KV cache**, which halves bytes/token from 114,688 to
57,344 and roughly doubles capacity to ~51 full-length sequences — enough to
hold all 48 without preemption, at some accuracy risk that would need its own
evaluation.

### Caveat I am not building on

`e2e_ms_p95` exceeds `wall_clock_s` in 12 of 13 rows by a consistent 9–18%,
which is physically odd if all requests are submitted simultaneously — a p95
cannot exceed the total run time. It may be client-side overhead outside the
timed window. I could not resolve it from the artefacts given, so no claim
above depends on that column. I would ask the harness author.

---

## B4 (3 pts)

I would pull **`vllm:num_requests_running`** (the gauge of sequences actually
in the running batch, as opposed to `num_requests_waiting`), sampled during
the batch-48 long-context run.

I expect it to **plateau at ~25**, not climb to 48, with
`vllm:num_requests_waiting` holding at ~23 for most of the run. That is the
single most direct confirmation of the B2 mechanism, because it distinguishes
between the two explanations that both predict falling throughput: "the GPU
is saturated and each sequence is simply slower" would show 48 running with a
much larger ITL, whereas "concurrency is capped by KV cache" shows ~25
running with ITL barely above the batch-24 value. The log's `itl_ms_p50` of
100.0 ms at batch 48 versus 96.07 ms at batch 24 already implies the second,
and this counter would confirm it directly rather than by inference.

Corroborating counter if a second were allowed: `vllm:num_preemptions_total`,
which should read 0 for every batch ≤ 24 and ≥ 23 at batch 48, and
`vllm:gpu_cache_usage_perc` pinned near 0.97.
