# 用于执行HIVE中的SQL语句

def update_document(cursor, content, version, did):
    """更新document_id=did的content或者version"""
    try:
        # cursor.execute(f"CREATE TABLE tmp AS SELECT * FROM documents WHERE document_id != '{did}'")
        # cursor.execute(f"INSERT INTO TABLE tmp VALUES('{content}', '{version}', '{did}')")
        # cursor.execute('INSERT OVERWRITE TABLE documents SELECT * FROM tmp')
        # cursor.execute('DROP TABLE tmp')
        cursor.execute(f"UPDATE documents SET content = '{content}', version = '{version}' WHERE document_id = '{did}'")
    except Exception as e:
        return False
    finally:
        return True

def delete_document(cursor, did):
    """删除document_id=did的文档"""
    try:
        # cursor.execute(f"CREATE TABLE tmp AS SELECT * FROM documents WHERE document_id != '{did}'")
        # cursor.execute('INSERT OVERWRITE TABLE documents SELECT * FROM tmp')
        # cursor.execute('DROP TABLE tmp')
        cursor.execute(f"DELETE FROM documents WHERE document_id = '{did}'")
    except Exception as e:
        return False
    finally:
        return True

def create_document(cursor, did):
    """创建一个名为did的document"""
    try:
        cursor.execute(f"INSERT INTO TABLE documents VALUES('', 'v0', '{did}')")
    except Exception as e:
        print(e)
        return False
    finally:
        return True

def list_documents(cursor):
    """获取documents"""
    try:
        cursor.execute('SELECT document_id FROM documents')
    except Exception as e:
        print(e)
        return False
    finally:
        return True