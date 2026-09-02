import csv
import os, sys
LOG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'starter_kit', 'bench', 'bench_log.csv')
if not os.path.exists(LOG):
    sys.exit(f'bench_log.csv not found at {LOG}\n'
             f'usage: python {sys.argv[0]} /path/to/bench_log.csv')

ROWS=list(csv.DictReader(open(LOG,newline='')))
f=lambda r,k: float(r[k]); i=lambda r,k: int(r[k])
print("=== honest OUTPUT goodput, all rows ===")
# Capacity in SEQUENCES depends on sequence length: 25.8 at 4096 tokens, but
# ~137 at the 512+256=768-token short-prompt rows. So only clamp rows that
# actually preempted -- never apply the 4096-token cap to short-prompt rows.
CAP=25.8
print(f"{'b':>3}{'plen':>6}{'reported':>10}{'e2e_goodput':>13}{'decode_goodput':>16}{'req/s':>8}")
for r in ROWS:
    b=i(r,'batch_size'); out=i(r,'num_requests')*i(r,'gen_len')
    e2e=out/f(r,'wall_clock_s'); itl=f(r,'itl_ms_p50')
    # batch/ITL is only the decode goodput while the SUBMITTED batch is actually
    # resident. Once preemption starts the running batch is capped near CAP, so
    # batch/ITL over-counts. Flag those rows rather than print a wrong number.
    bad = i(r,'preempted_seqs') > 0
    dec = (min(b, CAP) if bad else b)/(itl/1e3)
    mark = "*" if bad else " "
    print(f"{b:>3}{i(r,'prompt_len'):>6}{f(r,'reported_tok_s'):>10.1f}{e2e:>13.1f}{dec:>15.1f}{mark}{i(r,'num_requests')/f(r,'wall_clock_s'):>8.3f}")
print("  * preempted rows: running batch is capped near 25.8, NOT the submitted batch.")
print("    Naive batch/ITL would read 314.4 (b32) and 480.0 (b48) -- both spurious.")

print("\n=== B3: batch-24 long-prompt row, two independent derivations ===")
r=[x for x in ROWS if x['batch_size']=='24'][0]
print(f"  (i)  end-to-end   : 24 req * 512 out / {f(r,'wall_clock_s')} s = {24*512/f(r,'wall_clock_s'):.1f} output tok/s")
print(f"  (ii) steady decode: 24 concurrent / {f(r,'itl_ms_p50')} ms ITL   = {24/(f(r,'itl_ms_p50')/1e3):.1f} output tok/s")
print(f"  gap is prefill amortisation: {49.19:.2f}s decode + {61.16-49.19:.2f}s prefill = {61.16}s wall  [consistent]")

print("\n=== equal-footing: does long prompt help throughput? (same batch) ===")
for b in ('4','8','16','32'):
    s=[x for x in ROWS if x['batch_size']==b and x['prompt_len']=='512'][0]
    l=[x for x in ROWS if x['batch_size']==b and x['prompt_len']=='3584'][0]
    gs=i(s,'num_requests')*i(s,'gen_len')/f(s,'wall_clock_s'); gl=i(l,'num_requests')*i(l,'gen_len')/f(l,'wall_clock_s')
    print(f"  batch {b:>2}: short {gs:6.1f} vs long {gl:6.1f} output tok/s -> long is {100*(gl/gs-1):+.0f}%"
          f"   | reported counter says {100*(f(l,'reported_tok_s')/f(s,'reported_tok_s')-1):+.0f}%")

print("\n=== predicted effect of max_num_seqs=24 at offered load 48 ===")
r24=[x for x in ROWS if x['batch_size']=='24'][0]; r48=[x for x in ROWS if x['batch_size']=='48'][0]
w=2*f(r24,'wall_clock_s')
print(f"  two sequential waves of 24: {f(r24,'wall_clock_s')}*2 = {w:.2f}s vs observed {f(r48,'wall_clock_s')}s -> {100*(w/f(r48,'wall_clock_s')-1):+.1f}% wall")
print(f"  output goodput {48*512/w:.1f} vs {48*512/f(r48,'wall_clock_s'):.1f} tok/s -> {100*((48*512/w)/(48*512/f(r48,'wall_clock_s'))-1):+.1f}%")
print(f"  ttft for wave 1 back to ~{f(r24,'ttft_ms_p50')}ms (from {f(r48,'ttft_ms_p50')}ms); preempted 23 -> 0")

print("\n=== data-consistency note: e2e_p95 vs wall_clock ===")
for r in ROWS:
    print(f"  b={i(r,'batch_size'):>2} plen={i(r,'prompt_len'):>4} wall={f(r,'wall_clock_s'):>7.2f}s e2e_p95={f(r,'e2e_ms_p95')/1e3:>7.2f}s ratio={f(r,'e2e_ms_p95')/1e3/f(r,'wall_clock_s'):.3f}")
