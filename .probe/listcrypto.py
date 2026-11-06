import json, os, sys, zipfile, urllib.request, re
T = r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q"
libdir = os.path.join(T, "pylibs")
sys.path.insert(0, libdir)
meta = json.load(urllib.request.urlopen("https://pypi.org/pypi/cryptography/json", timeout=30))
names = [f["filename"] for f in meta["urls"]]
print("total files:", len(names))
for n in names:
    if "win_amd64" in n or "win32" in n:
        print("WIN:", n)
