import json, os, sys, zipfile, urllib.request

T = r"C:\Users\q8369\AppData\Local\Temp\dsh-fXE92q"
libdir = os.path.join(T, "pylibs")
os.makedirs(libdir, exist_ok=True)

try:
    import pypdf
    print("already:", pypdf.__version__)
    sys.exit(0)
except Exception:
    pass

meta = json.load(urllib.request.urlopen("https://pypi.org/pypi/pypdf/json", timeout=30))
url = None
for f in meta["urls"]:
    if f["packagetype"] == "bdist_wheel" and f["filename"].endswith(".whl"):
        url = f["url"]
        break
print("wheel:", url)
path = os.path.join(T, "pypdf.whl")
with urllib.request.urlopen(url, timeout=120) as r, open(path, "wb") as f:
    f.write(r.read())
print("downloaded bytes:", os.path.getsize(path))
with zipfile.ZipFile(path) as z:
    z.extractall(libdir)
print("extracted to:", libdir)
sys.path.insert(0, libdir)
import pypdf
print("OK pypdf", pypdf.__version__)
