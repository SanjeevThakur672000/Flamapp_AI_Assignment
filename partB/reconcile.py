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

ROWS=[]
with open(LOG,newline='') as f:
    for r in csv.DictReader(f):
        ROWS.append({k:(float(v) if '.' in v or k in('reported_tok_s','wall_clock_s','kv_cache_util') else int(v)) for k,v in r.items()})

print("=== H1: is reported_tok_s = num_requests*(prompt+gen)/wall? ===")
print(f"{'b':>3}{'plen':>6}{'reported':>10}{'total/wall':>12}{'out/wall':>10}{'err%':>8}")
for r in ROWS:
    tot=r['num_requests']*(r['prompt_len']+r['gen_len']); out=r['num_requests']*r['gen_len']
    pred=tot/r['wall_clock_s']; good=out/r['wall_clock_s']
    err=100*(pred-r['reported_tok_s'])/r['reported_tok_s']
    print(f"{r['batch_size']:>3}{r['prompt_len']:>6}{r['reported_tok_s']:>10.1f}{pred:>12.1f}{good:>10.1f}{err:>8.3f}")
