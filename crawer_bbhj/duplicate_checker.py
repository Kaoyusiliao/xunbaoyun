import sqlite3

conn = sqlite3.connect("bbhj_under18.sql")
c = conn.cursor()

# 检查1：按姓名+生日+失踪时间
c.execute("""
    SELECT 姓名, 生日, 失踪时间, COUNT(*) as cnt
    FROM 宝贝回家未成年
    GROUP BY 姓名, 生日, 失踪时间
    HAVING cnt > 1
""")
rows = c.fetchall()
if rows:
    print("发现重复 (姓名+生日+失踪时间):")
    for row in rows:
        print(f"  {row[0]}, {row[1]}, {row[2]} 出现 {row[3]} 次")
else:
    print("未发现完全匹配的重复记录（姓名+生日+失踪时间）。")

# 检查2：按姓名+生日（可能失踪时间不同但同一个人）
c.execute("""
    SELECT 姓名, 生日, COUNT(*) as cnt
    FROM 宝贝回家未成年
    GROUP BY 姓名, 生日
    HAVING cnt > 1
""")
rows = c.fetchall()
if rows:
    print("\n发现同名同生日但可能不同失踪时间的记录:")
    for row in rows:
        print(f"  {row[0]}, {row[1]} 出现 {row[2]} 次")
        # 列出这些记录的详情
        c2 = conn.cursor()
        c2.execute("SELECT id,失踪时间,失踪地址 FROM 宝贝回家未成年 WHERE 姓名=? AND 生日=?", (row[0], row[1]))
        for detail in c2.fetchall():
            print(f"      id={detail[0]}, 失踪时间={detail[1]}, 地址={detail[2]}")
else:
    print("未发现同名同生日的重复记录。")

conn.close()