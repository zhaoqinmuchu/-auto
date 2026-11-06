import re, sys, zlib, os

paths = [
    r"yuanwen\第一册《市场哲学的数学原理完全配图手册》.pdf",
    r"yuanwen\第六册《市场哲学的数学原理完全配图手册》.pdf",
]
for p in paths:
    print("=" * 70)
    print("FILE:", p, os.path.getsize(p))
    with open(p, "rb") as f:
        data = f.read()
    print("header:", data[:20])
    for key in [b"/Producer", b"/Creator", b"/Title"]:
        for m in re.finditer(re.escape(key) + rb"\s*\(([^)]{0,120})\)", data[:200000]):
            print(key.decode(), "->", m.group(1)[:120])
            break
    print("pages(/Type/Page count):", len(re.findall(rb"/Type\s*/Page[^s]", data)))
    print("/Count entries:", re.findall(rb"/Count\s+(\d+)", data)[:5])
    print("/ToUnicode count:", data.count(b"/ToUnicode"))
    print("/FontFile count:", data.count(b"/FontFile"), "/FontFile2:", data.count(b"/FontFile2"), "/FontFile3:", data.count(b"/FontFile3"))
    print("/Type0:", data.count(b"/Type0"), "/TrueType:", data.count(b"/TrueType"), "/Type1:", data.count(b"/Type1"), "/Type3:", data.count(b"/Type3"))
    print("/ObjStm:", data.count(b"/ObjStm"), "/XRefStm:", data.count(b"/XRefStm"))
    print("/DCTDecode(images):", data.count(b"/DCTDecode"), "/JPXDecode:", data.count(b"/JPXDecode"), "/CCITTFaxDecode:", data.count(b"/CCITTFaxDecode"))
    # try decompressing the first few streams
    ok = 0; samples = []
    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        raw = data[start:end]
        try:
            d = zlib.decompress(raw)
            ok += 1
            if len(samples) < 3:
                samples.append(d[:400])
        except Exception:
            pass
        if ok > 5 and len(samples) >= 3:
            break
    print("decompressible streams in first scan:", ok)
    for s in samples:
        print("---- sample stream head ----")
        print(s[:400])
