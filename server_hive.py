from concurrent import futures
import grpc
import time
from pyhive import hive
import document_pb2
import document_pb2_grpc
import logging
from kazoo.client import KazooClient, KazooState
from kazoo.exceptions import LockTimeout
import hive_operation as hop

# 分布式设置
HIVE_HOST = 'localhost'
HIVE_PORT = 10000
HIVE_USERNAME = 'linbei'
ZOOKEEPER_HOSTS = 'localhost:2181'

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 日志格式
    handlers=[
        logging.FileHandler("logs/app.log"),  # 将日志输出到文件
        logging.StreamHandler()  # 将日志输出到控制台
    ]
)
logger = logging.getLogger(__name__)

# 需要检查数据库是否存在！！！！！！
class DocumentServiceServicer(document_pb2_grpc.DocumentServiceServicer):

    def __init__(self):
        """
        初始化函数，检查HIVE中是否已有表格 documents；
        若无，则需要创建表格；documents的形式：
        ##############################
        content                 string
        version                 string
        document_id             string
        ##############################
        """
        self.zk = KazooClient(hosts=ZOOKEEPER_HOSTS)
        self.zk.start()
        conn = self.get_hive_connection()
        cursor = conn.cursor()
        try: 
            cursor.execute("DESCRIBE documents")
            logger.info("TABLE: documents is exit.")
        except Exception as e:
            if 'SemanticException' in str(e):
                logger.info('SemanticException in Server INIT, to Create TABLE documents')
                cursor.execute("\
                        CREATE TABLE documents(content STRING, version STRING, document_id STRING) \
                        CLUSTERED BY(document_id) INTO 3 BUCKETS  \
                        STORED AS ORC   \
                        TBLPROPERTIES ('transactional'='true')   \
                    ")
                logger.info("TABLE documents has been created.")
        finally:
            # 关闭游标和连接
            cursor.close()
            conn.close()
        

    def get_hive_connection(self):
        """链接HIVE数据库"""
        return hive.Connection(
            host=HIVE_HOST, port=HIVE_PORT, username=HIVE_USERNAME
        )
    
    def ReadDocument(self, request, context):
        """ 根据请求request，获取文档 """
        conn = self.get_hive_connection()
        cursor = conn.cursor()
        logger.info(f"Request to ReadDocument: {request.document_id}")
        op = f"SELECT content, version FROM documents WHERE document_id = '{request.document_id}'"
        cursor.execute(op)
        result = cursor.fetchone()
        if result:
            logger.info('Document Found')
            content, version = result
            return document_pb2.ReadResponse(content=content, version=version)
        else:
            logger.info('Document NOT Found')
            context.set_details('Document not found')
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return document_pb2.ReadResponse()

    def WriteDocument(self, request, context):
        """根据请求，写入文档，使用zookeeper实现互斥"""
        #定义锁的路径
        lock_path = f"/locks/{request.document_id}"
        # 创建锁对象
        lock = self.zk.Lock(lock_path, "document_lock")

        try:
            # 尝试获取锁
            if lock.acquire(timeout=10):
                conn = self.get_hive_connection()
                with conn.cursor() as cursor:
                    logger.info(f'Request to WriteDocument: {request.document_id}')
                    op = f"SELECT version FROM documents WHERE document_id = '{request.document_id}'"
                    cursor.execute(op)
                    current_version = cursor.fetchone()
                    if not current_version or current_version[0] != request.version:
                        context.set_details("version mismatch or document not found")
                        logger.info(f'Current version = {current_version}, Found version = {request.version}')
                        context.set_code(grpc.StatusCode.ABORTED)
                        return document_pb2.WriteResponse(success=False, message="version mismatch or document not found")
                    
                    new_version = f"v{int(request.version[1:]) + 1}"
                    # cursor.execute("UPDATE documents SET content = %s, version = %s WHERE document_id = %s", 
                    #             (request.content, new_version, request.document_id))
                    exec_feedback = hop.update_document(cursor, request.content, new_version, request.document_id)
                    if exec_feedback:
                        conn.commit()
                        logger.info('WriteDocument OK. Has Been commit.')
                        return document_pb2.WriteResponse(success=True, message="Document updated")
                    else:
                        context.set_details("SQL update ERROR")
                        context.set_code(grpc.StatusCode.ABORTED)
                        logger.info('WriteDocument Failed. SQL ERROR. To rollback.')
                        conn.rollback()
                        return document_pb2.WriteResponse(success=false, message="SQL update ERROR")
            else:
                context.set_details("Could not acquire lock")
                context.set_code(grpc.StatusCode.ABORTED)
                logger.info('Could not acquire lock')
                return document_pb2.WriteResponse(success=False, message="Could not acquie lock")

        except LockTimeout:
            # 锁超时
            context.set_details("Lock acquisition timed out")
            context.set_code(grpc.StatusCode.ABORTED)
            logger.info('Lock acquisition timed out')
            return document_pb2.WriteResponse(success=False, message="Lock acquisition timed out")
        finally:
            # 释放锁
            lock.release()

    def CreateDocument(self, request, context):
        """ 根据请求request，创建文档"""
        conn = self.get_hive_connection()
        cursor = conn.cursor()
        logger.info(f"Request to ReadDocument: {request.document_id}")
        cursor.execute(f"SELECT content, version FROM documents WHERE document_id = '{request.document_id}'")
        search_res = cursor.fetchone()
        if search_res:
            logger.info(f'Document {request.document_id} Exit.')
            context.set_details('Document Exist, cannot create.')
            context.set_code(grpc.StatusCode.ABORTED)
            return document_pb2.CreateResponse(success=False, message='Document Exist.')
        else:
            logger.info(f'Document {request.document_id} not exist, can create.')
            create_res = hop.create_document(cursor, request.document_id)
            if create_res:
                logger.info(f'Document {request.document_id} create successfully.')
                return document_pb2.CreateResponse(success=True, message='Document Created.')
            else:
                logger.info(f'Document {request.document_id} create failed.')
                return document_pb2.CreateResponse(success=False, message='HIVE Error.')

    def DeleteDocument(self, request, context):
        """根据请求request，删除文档"""
        conn = self.get_hive_connection()
        cursor = conn.cursor()
        logger.info(f"Request to ReadDocument: {request.document_id}")
        cursor.execute(f"SELECT content, version FROM documents WHERE document_id = '{request.document_id}'")
        search_res = cursor.fetchone()
        if not search_res:
            logger.info(f'Document {request.document_id} no Exist')
            context.set_details('Document not Exist, cannot delete.')
            context.set_code(grpc.StatusCode.ABORTED)
            return document_pb2.DeleteResponse(success=False, message='Document not Exist.')
        else:
            logger.info(f'Document {request.document_id} exist, can delete.')
            delete_res = hop.delete_document(cursor, request.document_id)
            if delete_res:
                logger.info(f'Document {request.document_id} delete successfully.')
                return document_pb2.DeleteResponse(success=True, message='Document Delete.')
            else:
                logger.info(f'Document {request.document_id} delete failed.')
                return document_pb2.DeleteResponse(success=False, message='HIVE Error.')

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    document_pb2_grpc.add_DocumentServiceServicer_to_server(DocumentServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC server running on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()