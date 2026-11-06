import os, sys, time, re
T = r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q"
sys.path.insert(0, os.path.join(T, "pylibs"))
from pypdf import PdfReader

p = sys.argv[1] if len(sys.argv) > 1 else r"yuanwen\第一册《市场哲学的数学原理完全配图手册》.pdf"
t0 = time.time()
r = PdfReader(p)
print("pages:", len(r.pages), "meta:", r.metadata)
txt = []
for i, pg in enumerate(r.pages[:3]):
    t = pg.extract_text() or ""
    print(f"---- page {i+1} len={len(t)} chars, {time.time()-t0:.1f}s ----")
    print(t[:600])
