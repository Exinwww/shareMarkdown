# 用于测试是否可以链接到Hive

from pyhive import hive

# Hive 连接信息
host = 'localhost'  # Hive 主机名或 IP 地址
port = 10000             # 默认 Hive 端口号
username = 'linbei'  # 登录 Hive 的用户名 ！！！需要有权限！！！！

# 创建 Hive 连接
conn = hive.Connection(host=host, port=port, username=username)

# 创建游标
cursor = conn.cursor()

did = '12345'
# 执行 SQL 查询
# cursor.execute('SHOW DATABASES')
# cursor.execute(f"CREATE TABLE tmp AS SELECT * FROM documents WHERE document_id != {did}")
# cursor.execute(f"INSERT INTO TABLE tmp VALUES('hahaha', 'v2', '12345')")
# cursor.execute('INSERT OVERWRITE TABLE documents SELECT * FROM tmp')
# cursor.execute('\
#     DROP TABLE tmp\
# ')
# # 获取查询结果
# databases = cursor.fetchall()

# # 打印结果
# print('Databases:')
# for db in databases:
#     print(db[0])

try:
    cursor.execute('SELECT * FROM HAHA')
except Exception as e:
    print('got error')
    print(e)

# 关闭游标和连接
cursor.close()
conn.close()
