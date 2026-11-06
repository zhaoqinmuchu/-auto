# -*- coding: utf-8 -*-
"""生成"单条 PLOYLINE（变量版）"测试公式：
L: 300 顶点，一条折线（变量 V1..V300 + SUM 汇总 + 一条 PLOYLINE）
M: 2 条折线 × 150 顶点（备用，若语句数受限）
顶点 = AUL9 5 分钟 TXT 的最后 600 根每 2 根取 1（与 H 相同），价格 = 该根收盘价。
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
    return f"(DATE={1000000 + (v['y'] % 100) * 10000 + v['mo'] * 100 + v['d']} AND TIME={v['hh'] * 100 + v['mm']})"


def build(vertices, name):
    lines = [
        "{ " + name + " }",
        "{ 单条 PLOYLINE + 变量版：验证『一条折线无分块』是否没有乱飞射线 }",
        "{ 预期：一条黄色折线沿价格走完全程（每 2 根 5 分钟 K 线取 1 个顶点），不跨图斜飞 }",
    ]
    for i, v in enumerate(vertices, 1):
        lines.append(f"V{i}:=IF({cond_str(v)},{v['c']:.2f},0);")
    total = len(vertices)
    lines.append("SUM:=" + "+".join(f"V{i}" for i in range(1, total + 1)) + ";")
    lines.append("PLOYLINE(SUM>0,SUM),COLORYELLOW;")
    return "\n".join(lines) + "\n"


def main():
    rows = load_rows()
    print("rows:", len(rows), "first:", rows[0]["y"], rows[0]["mo"], rows[0]["d"], rows[0]["hh"], rows[0]["mm"],
          "last:", rows[-1]["y"], rows[-1]["mo"], rows[-1]["d"], rows[-1]["hh"], rows[-1]["mm"])
    block = rows[-600:]
    verts = block[::2][:300]
    print("vertices:", len(verts), "first idx in rows:", len(rows) - 600, "first:", verts[0], "last:", verts[-1])

    p_l = OUT_DIR / "tdx_测试L_单折线300顶点_变量版.txt"
    p_l.write_text(build(verts, "测试L：单折线 300 顶点"), encoding="utf-8")
    print("written", p_l, p_l.stat().st_size)

    # 备用 M：拆成 2 条折线，每条 150 顶点
    lines = ["{ 测试M：2 条折线，每条 150 顶点（备用） }", "{ 预期：两条折线各自沿价格走，只有末尾各有 1 条射线 }"]
    for chunk_i, chunk in enumerate([verts[:150], verts[150:]], 1):
        for i, v in enumerate(chunk, 1):
            lines.append(f"W{chunk_i}_{i}:=IF({cond_str(v)},{v['c']:.2f},0);")
        lines.append(f"S{chunk_i}:=" + "+".join(f"W{chunk_i}_{i}" for i in range(1, len(chunk) + 1)) + ";")
        lines.append(f"PLOYLINE(S{chunk_i}>0,S{chunk_i}),COLORYELLOW;")
    p_m = OUT_DIR / "tdx_测试M_两条折线各150顶点.txt"
    p_m.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("written", p_m, p_m.stat().st_size)


if __name__ == "__main__":
    main()
