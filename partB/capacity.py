import csv
import os, sys

def _find(rel):
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    for up in (".", "..", "../..", "../../.."):
        c = os.path.normpath(os.path.join(here, up, rel))
        if os.path.exists(c):
            return c
    return os.path.normpath(os.path.join(here, "..", rel))
LOG = sys.argv[1] if len(sys.argv) > 1 else _find('starter_kit/bench/bench_log.csv')
if not os.path.exists(LOG):
    sys.exit(f'bench_log.csv not found at {LOG}\n'
             f'usage: python {sys.argv[0]} /path/to/bench_log.csv')

L,KVH,HD,BY = 28,8,128,2
P,PBY = 4.2e9,2
GPU_GB, UTIL, OVER_GB = 24, 0.92, 1.6
BW = 300e9; TFLOPS=121e12

kv_tok = 2*KVH*HD*BY*L
print("=== B1a KV bytes/token ===")
print(f"per layer = 2(K,V) * {KVH} kv_heads * {HD} head_dim * {BY}B = {2*KVH*HD*BY} B")
print(f"x {L} layers = {kv_tok} B/token = {kv_tok/1024:.0f} KiB/token = {kv_tok/1e3:.3f} kB/token")

print("\n=== B1b max concurrent 4096-tok seqs ===")
for name,U in (("decimal GB (1e9)",1e9),("binary GiB (2**30)",2**30)):
    budget=GPU_GB*UTIL*U; w=P*PBY; ov=OVER_GB*U
    kv=budget-w-ov; per=4096*kv_tok
    print(f"{name:>20}: budget {budget/U:.2f} - weights {w/U:.2f} - overhead {ov/U:.2f} = {kv/U:.2f} for KV")
    print(f"{'':>20}  per seq 4096*{kv_tok} = {per/U:.4f} -> floor({kv/per:.2f}) = {int(kv//per)} seqs")

print("\n=== check against log ===")
ROWS=list(csv.DictReader(open(LOG,newline='')))
for r in ROWS:
    if r['prompt_len']!='3584': continue
    b=int(r['batch_size']); u=float(r['kv_cache_util']); pre=int(r['preempted_seqs'])
    # once kv_util clamps at its ceiling, b/util no longer measures capacity
    cap = f"{b/u:5.1f}" if pre == 0 else "  n/a"
    print(f" b={b:>2} kv_util={u:.2f} preempted={pre:>2} | implied_cap_from_util={cap} | b-preempted={b-pre:>2}")

print("\n=== decode roofline: bytes read per decode step ===")
print(f"{'b':>3}{'GB/step':>9}{'ITL_roof_ms':>13}{'ITL_obs':>9}{'MBU':>7}{'implied_running_seqs':>22}")
for r in ROWS:
    if r['prompt_len']!='3584': continue
    b=int(r['batch_size']); itl=float(r['itl_ms_p50'])
    mean_ctx = 3584+512/2
    byt = P*PBY + b*mean_ctx*kv_tok
    roof = byt/BW*1e3
    # implied running seqs: solve roof(n)/mbu = itl using mbu from b=16 row
    print(f"{b:>3}{byt/1e9:>9.2f}{roof:>13.2f}{itl:>9.2f}{roof/itl:>7.3f}", end="")
    mbu=0.667
    n=((itl/1e3*BW*mbu)-P*PBY)/(mean_ctx*kv_tok)
    print(f"{n:>22.1f}")

print("\n=== prefill accounting for b=24 long row ===")
r=[x for x in ROWS if x['batch_size']=='24'][0]
wall=float(r['wall_clock_s']); itl=float(r['itl_ms_p50'])
dec = 512*itl/1e3
print(f"wall={wall}s ; decode = 512 steps * {itl}ms = {dec:.2f}s ; residual prefill = {wall-dec:.2f}s")
pt=24*3584; fl=2*P*pt
print(f"prefill tokens={pt}  FLOPs=2*{P:.1e}*{pt}={fl:.3e}  roofline={fl/TFLOPS:.2f}s  MFU={fl/TFLOPS/(wall-dec):.3f}")
