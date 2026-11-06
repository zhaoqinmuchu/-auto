import baostock as bs

lg = bs.login()
rs = bs.query_stock_basic()
cnt = 0
rows = []
while (rs.error_code == '0') and rs.next():
    rows.append(rs.get_row_data())
    cnt += 1
    if cnt >= 5:
        break

for r in rows:
    raw = r[1]
    # 尝试不同编码解码
    try:
        decoded = raw.encode('latin1').decode('gbk')
        print("latin1->gbk:", decoded)
    except Exception as e:
        print("latin1->gbk fail:", e)
        print("raw:", repr(raw))

bs.logout()
