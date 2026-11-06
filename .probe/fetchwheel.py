import json, os, sys, zipfile, urllib.request, re
T = r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q"
libdir = os.path.join(T, "pylibs")
sys.path.insert(0, libdir)

def score(name: str):
    if "win_amd64" not in name:
        return -1
    if re.search(r"cp314-cp314(t)?-win_amd64", name):
        return 100
    m = re.search(r"cp3(\d+)-abi3-win_amd64", name)
    if m:
        return 80 + int(m.group(1))
    if "py3-none-any" in name:
        return 10
    return -1

def fetch(pkg):
    meta = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json", timeout=30))
    best = None; bs = -1
    for f in meta["urls"]:
        if f["packagetype"] != "bdist_wheel":
            continue
        s = score(f["filename"])
        if s > bs:
            bs, best = s, f
    if not best:
        print("no wheel", pkg); return False
    print("picked:", best["filename"], "score", bs)
    path = os.path.join(T, best["filename"])
    with urllib.request.urlopen(best["url"], timeout=300) as r, open(path, "wb") as fh:
        fh.write(r.read())
    with zipfile.ZipFile(path) as z:
        z.extractall(libdir)
    print("extracted", best["filename"], os.path.getsize(path))
    return True

for pkg in sys.argv[1:]:
    fetch(pkg)
