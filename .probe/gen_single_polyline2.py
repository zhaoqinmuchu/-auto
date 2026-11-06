# -*- coding: utf-8 -*-
"""v2：变量名避开通达信函数名/下划线，SUM 改为分层汇总（每句 ≤25 个操作数）。

L2: 300 顶点，单条折线：V1..V300 → G1..G12（每 25 个一组）→ TOTV → PLOYLINE
M2: 200 顶点，两条折线（各 100 顶点，分色），用于"已确定/未确定"或备用
"""
import re
from pathlib import Path

SRC = Path(r"C:\Users\q8369\Desktop\AUL9.txt")
OUT_DIR = Path(r"C:\Users\q8369\Desktop")


def load_rows():
    rows = []
    for ln in SRC.read_text(encoding="gbk", errors="replace").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        parts = re.split(r"\s+", s)
        if len(parts) < 5:
            continue
        m = re.match(r"(\d{4})/(\d{2})/(\d{2})-(\d{2}):(\d{2})$", parts[0])
        if not m:
            continue
        y, mo, d, hh, mm = (int(x) for x in m.groups())
        o, h, l, c = (float(x) for x in parts[1:5])
        rows.append(dict(y=y, mo=mo, d=d, hh=hh, mm=mm, o=o, h=h, l=l, c=c))
    return rows


def cond_str(v):
    date = 1000000 + (v["y"] % 100) * 10000 + v["mo"] * 100 + v["d"]
    return f"(DATE={date} AND TIME={v['hh'] * 100 + v['mm']})"


def emit_vertices(vertices, prefix):
    """每个顶点一句；返回 (语句列表, 变量名列表)"""
    lines, names = [], []
    for i, v in enumerate(vertices, 1):
        name = f"{prefix}{i}"
        lines.append(f"{name}:=IF({cond_str(v)},{v['c']:.2f},0);")
        names.append(name)
    return lines, names


def emit_group_sum(names, group_prefix, out_name, group_size=25):
    """把变量名按 group_size 分组求和，最后再汇总；避免单句操作数过多。"""
    lines = []
    group_names = []
    for gi in range(0, len(names), group_size):
        chunk = names[gi:gi + group_size]
        gname = f"{group_prefix}{len(group_names) + 1}"
        lines.append(f"{gname}:=" + "+".join(chunk) + ";")
        group_names.append(gname)
    if len(group_names) > 1:
        lines.append(f"{out_name}:=" + "+".join(group_names) + ";")
        return lines, out_name
    return lines, group_names[0]


def main():
    rows = load_rows()
    print("rows:", len(rows))
    block = rows[-600:]
    verts = block[::2][:300]
    print("vertices:", len(verts), "first:", verts[0], "last:", verts[-1])

    # ---------- L2：单条折线 300 顶点 ----------
    lines = [
        "{ 测试L2：单折线 300 顶点（变量名无下划线、分层求和） }",
        "{ 预期：一条黄色折线沿价格走完全程；末尾之后只有极短射线 }",
    ]
    vlines, vnames = emit_vertices(verts, "V")
    lines += vlines
    slines, sum_name = emit_group_sum(vnames, "G", "TOTV", 25)
    lines += slines
    lines.append(f"PLOYLINE({sum_name}>0,{sum_name}),COLORYELLOW;")
    p = OUT_DIR / "tdx_测试L2_单折线300顶点.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("written", p, p.stat().st_size, "statements:", len(lines))

    # ---------- M2：两条折线（各 150 顶点，分色） ----------
    half = len(verts) // 2
    lines = [
        "{ 测试M2：两条折线（各 150 顶点，黄=前段 红=后段） }",
        "{ 预期：两条线首尾相接沿价格走；各自末尾只有极短射线 }",
    ]
    alines, anames = emit_vertices(verts[:half], "A")
    blines, bnames = emit_vertices(verts[half:], "B")
    lines += alines + blines
    aslines, asum = emit_group_sum(anames, "GA", "TA", 25)
    bslines, bsum = emit_group_sum(bnames, "GB", "TB", 25)
    lines += aslines + bslines
    lines.append(f"PLOYLINE({asum}>0,{asum}),COLORYELLOW;")
    lines.append(f"PLOYLINE({bsum}>0,{bsum}),COLORRED;")
    p2 = OUT_DIR / "tdx_测试M2_两条折线各150顶点.txt"
    p2.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("written", p2, p2.stat().st_size, "statements:", len(lines))


if __name__ == "__main__":
    main()
