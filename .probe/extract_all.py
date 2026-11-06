import os, sys, time, traceback
T = r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q"
sys.path.insert(0, os.path.join(T, "pylibs"))
from pypdf import PdfReader

WS = r"C:\Users\q8369\Documents\ChatGPT\chan.py-main"
OUT = os.path.join(T, "yuanwen_txt")
os.makedirs(OUT, exist_ok=True)

files = sorted(os.listdir(os.path.join(WS, "yuanwen")))
for fn in files:
    if not fn.lower().endswith(".pdf"):
        continue
    src = os.path.join(WS, "yuanwen", fn)
    dst = os.path.join(OUT, os.path.splitext(fn)[0] + ".txt")
    if os.path.exists(dst) and os.path.getsize(dst) > 10000:
        print("skip existing", fn, os.path.getsize(dst), flush=True)
        continue
    t0 = time.time()
    try:
        r = PdfReader(src)
        n = len(r.pages)
        parts = []
        empty = 0
        for i, pg in enumerate(r.pages):
            try:
                t = pg.extract_text() or ""
            except Exception as e:
                t = f"[EXTRACT_ERROR {e}]"
            if not t.strip():
                empty += 1
            parts.append(f"\n\n===== [VOL={fn}] [PAGE={i+1}] =====\n{t}")
            if (i + 1) % 50 == 0:
                print(f"  {fn}: {i+1}/{n} pages, {time.time()-t0:.0f}s", flush=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.writelines(parts)
        print(f"DONE {fn}: {n} pages, empty={empty}, {os.path.getsize(dst)} bytes, {time.time()-t0:.0f}s", flush=True)
    except Exception:
        print("FAILED", fn, flush=True)
        traceback.print_exc()
print("ALL DONE", flush=True)
