import json, os, sys, zipfile, urllib.request

T = r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q"
libdir = os.path.join(T, "pylibs")
os.makedirs(libdir, exist_ok=True)
sys.path.insert(0, libdir)

def fetch(pkg, picker):
    meta = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json", timeout=30))
    cands = [f for f in meta["urls"] if f["packagetype"] == "bdist_wheel"]
    for f in cands:
        if picker(f["filename"]):
            print("picked:", f["filename"])
            path = os.path.join(T, f["filename"])
            with urllib.request.urlopen(f["url"], timeout=180) as r, open(path, "wb") as fh:
                fh.write(r.read())
            with zipfile.ZipFile(path) as z:
                z.extractall(libdir)
            print("extracted:", f["filename"], os.path.getsize(path))
            return True
    print("NO MATCH for", pkg, [f["filename"] for f in cands][:10])
    return False

fetch("cryptography", lambda n: "win_amd64" in n and "cp38-abi3" in n and "cp311" in n)
try:
    import cryptography
    print("cryptography OK", cryptography.__version__)
except Exception as e:
    print("import failed:", e)
