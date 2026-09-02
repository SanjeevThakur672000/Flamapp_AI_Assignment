import unicodedata, regex
import sys
import os
_DEF=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','starter_kit','corpus_sample')
D=(sys.argv[1] if len(sys.argv)>1 else _DEF)+'/'
if not os.path.isdir(D): sys.exit(f'corpus_sample not found at {D}\nusage: python {sys.argv[0]} /path/to/corpus_sample')
def load(p):
    return [unicodedata.normalize("NFC",l.strip()) for l in open(D+p,encoding='utf-8') if l.strip()]
E,H=load('eng_sample.txt'),load('hin_sample.txt')

print("=== C1. split(' ') vs split() : the word-count bug ===")
for name,ls in (('eng',E),('hin',H)):
    b=sum(len(l.split(" ")) for l in ls); g=sum(len(l.split()) for l in ls)
    print(f" {name}: split(' ')={b:>3}  split()={g:>3}  inflation={100*(b/g-1):+.2f}%")
    for i,l in enumerate(ls,1):
        if len(l.split(" "))!=len(l.split()):
            print(f"    line {i}: {len(l.split(' '))} vs {len(l.split())}  ->  {l!r}")

print("\n=== C2. denominators, exact counts (no tokenizer needed) ===")
print(f"{'lang':<6}{'lines':>6}{'words':>7}{'codepts':>9}{'graphemes':>11}{'utf8_bytes':>12}{'cp/word':>9}{'gr/word':>9}{'B/word':>8}")
tot={}
for name,ls in (('eng',E),('hin',H)):
    w=sum(len(l.split()) for l in ls); cp=sum(len(l) for l in ls)
    gr=sum(len(regex.findall(r'\X',l)) for l in ls); by=sum(len(l.encode()) for l in ls)
    tot[name]=(w,cp,gr,by)
    print(f"{name:<6}{len(ls):>6}{w:>7}{cp:>9}{gr:>11}{by:>12}{cp/w:>9.2f}{gr/w:>9.2f}{by/w:>8.2f}")

print("\n=== C3. REPORT_v0 Finding 2/3 checked against REPORT_v0's own table ===")
fe,te,fh,th = 1.27,0.226,7.45,1.579
print(f"  fertility ratio hin/eng = {fh/fe:.2f}   (report: 5.89)")
print(f"  tok/char  ratio hin/eng = {th/te:.2f}   (report: 7.0)")
print("  identity: (tok/word)/(tok/char) = char/word  -- shared numerator, NOT independent")
print(f"    eng chars/word implied by report = {fe/te:.2f} ; measured on corpus = {tot['eng'][1]/tot['eng'][0]:.2f}")
print(f"    hin chars/word implied by report = {fh/th:.2f} ; measured on corpus = {tot['hin'][1]/tot['hin'][0]:.2f}")
print(f"    ratio of the two ratios = {(th/te)/(fh/fe):.3f} = eng_cpw/hin_cpw = {(fe/te)/(fh/th):.3f}")
print(f"  => report claim 3 ('Hindi has more Unicode characters per word') is FALSE by its own numbers:")
print(f"     hin {tot['hin'][1]/tot['hin'][0]:.2f} cp/word < eng {tot['eng'][1]/tot['eng'][0]:.2f} cp/word")
print(f"     but hin uses {tot['hin'][3]/tot['hin'][2]:.2f} utf8 bytes/grapheme vs eng {tot['eng'][3]/tot['eng'][2]:.2f}")

print("\n=== C4. are the two files actually parallel line-by-line? ===")
print("  (assignment says 'parallel'; content inspection says otherwise)")
pairs={3:3,4:7,5:6,7:10,8:4}
print("  hand-alignment of translatable pairs:", pairs)
print(f"  eng lines with no Hindi counterpart: {sorted(set(range(1,11))-set(pairs))}")
print(f"  hin lines with no English counterpart: {sorted(set(range(1,11))-set(pairs.values()))}")
