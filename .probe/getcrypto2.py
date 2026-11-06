import json, os, sys, zipfile, urllib.request
T = r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q"
libdir = os.path.join(T, "pylibs")
sys.path.insert(0, libdir)
target = "cryptography-50.0.2-cp311-abi3-win_amd64.whl"
meta = json.load(urllib.request.urlopen("https://pypi.org/pypi/cryptography/json", timeout=30))
url = [f["url"] for f in meta["urls"] if f["filename"] == target][0]
path = os.path.join(T, target)
with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
    f.write(r.read())
print("size:", os.path.getsize(path))
with zipfile.ZipFile(path) as z:
    z.extractall(libdir)
print("extracted")
import cryptography
print("cryptography OK", cryptography.__version__)
