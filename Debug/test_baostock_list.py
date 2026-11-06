import baostock as bs

lg = bs.login()
print("login:", lg.error_code, lg.error_msg)

rs = bs.query_stock_basic()
print("query error_code:", rs.error_code, rs.error_msg)
print("fields:", rs.fields)

cnt = 0
rows = []
while (rs.error_code == '0') and rs.next():
    rows.append(rs.get_row_data())
    cnt += 1

print("total:", cnt)
print("sample:", rows[:5])

bs.logout()
