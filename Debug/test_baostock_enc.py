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
    print(repr(r[1]))

bs.logout()
