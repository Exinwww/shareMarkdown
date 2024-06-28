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
import redis
from concurrent.futures import ThreadPoolExecutor
import json

# 分布式设置
HIVE_HOST = 'localhost'
HIVE_PORT = 10000
HIVE_USERNAME = 'linbei'
ZOOKEEPER_HOSTS = 'localhost:2181'
redis_client = redis.Redis(host='localhost', port=6379, db=2)
# 配置日志记录
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 日志格式
    handlers=[
        logging.FileHandler("logs/app_server.log"),  # 将日志输出到文件
        logging.StreamHandler()  # 将日志输出到控制台
    ]
)
logger = logging.getLogger(__name__)

def get_hive_connection():
    """链接HIVE数据库"""
    return hive.Connection(
        host=HIVE_HOST, port=HIVE_PORT, username=HIVE_USERNAME
    )
def update_hive(key, value, op_type):
    conn = self.get_hive_connection()
    cursor = conn.cursor()
     #定义锁的路径
    lock_path = f"/locks/{key}"
    # 创建锁对象
    lock = self.zk.Lock(lock_path, "document_lock")
    try:
        if lock.acquire(timeout=10):
            if op_type=='write':
                content = value['content']
                version = value['version']
                hop.update_document(cursor, content, version, key)
            elif op_type == 'delete':
                hop.delete_document(cursor, key)
            elif op_type == 'create':
                hop.create_document(cursor, key)
    # except LockTimeout:
    #     # 锁超时
    finally:
        # 释放锁
        lock.release()
        
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
        # 创建线程池
        self.executor = ThreadPoolExecutor(max_workers=5)
        conn = get_hive_connection()
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

            op = f"SELECT * FROM documents"
            cursor.execute(op)
            results = cursor.fetchall()
            for item in results:
                did = item[2]
                content = item[0]
                version = item[1]
                data = {
                    'content': content,
                    'version': version
                }
                redis_client.set(did, json.dumps(data))

            cursor.close()
            conn.close()
        

    
    
    def ReadDocument(self, request, context):
        """ 根据请求request，获取文档 """
        logger.info('Request to READ Documents')
        values = redis_client.get(request.document_id)
        if not values: #没找到
            logger.info('Document NOT Found')
            context.set_details('Document not found')
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return document_pb2.ReadResponse()
        else: # 找到
            values = json.loads(values)
            content = values['content']
            version = values['version']
            return document_pb2.ReadResponse(content=content, version=version)

    def WriteDocument(self, request, context):
        logger.info('Request to WRITE Documents')
        values = redis_client.get(request.document_id)
        if not values:
            context.set_details("version mismatch or document not found")
            logger.info(f'Current version = {current_version}, Found version = {request.version}')
            context.set_code(grpc.StatusCode.ABORTED)
            return document_pb2.WriteResponse(success=False, message="version mismatch or document not found")
        values = json.loads(values)
        if values['version'] != request.version:
            context.set_details("version mismatch or document not found")
            logger.info(f'Current version = {current_version}, Found version = {request.version}')
            context.set_code(grpc.StatusCode.ABORTED)
            return document_pb2.WriteResponse(success=False, message="version mismatch or document not found")

        new_version = f"v{int(request.version[1:]) + 1}"
        write_data = {
            'version':new_version,
            'content':request.content
        }
        redis_client.set(request.document_id, json.dumps(write_data))
        self.executor.submit(update_hive, request.document_id, write_data, 'write')

        logger.info('WriteDocument OK. Has Been commit.')
        return document_pb2.WriteResponse(success=True, message="Document updated")

    def CreateDocument(self, request, context):
        """ 根据请求request，创建文档"""
        logger.info('Request to CREATE Documents')
        values = redis_client.get(request.document_id)
        if values: # 找到
            values = json.loads(values)
            logger.info(f'Document {request.document_id} Exit.')
            context.set_details('Document Exist, cannot create.')
            context.set_code(grpc.StatusCode.ABORTED)
            return document_pb2.CreateResponse(success=False, message='Document Exist.')
        else:
            create_data = {
                'version':'v0',
                'content': ''
            }
            redis_client.set(request.document_id, json.dumps(create_data))
            self.executor.submit(update_hive, request.document_id, create_data, 'create')
            return document_pb2.CreateResponse(success=True, message='Document Created.')

    def DeleteDocument(self, request, context):
        """根据请求request，删除文档"""
        logger.info('Request to DELETE Documents')
        values = redis_client.get(request.document_id)
        if not values: # 没找到
            logger.info(f'Document {request.document_id} no Exist')
            context.set_details('Document not Exist, cannot delete.')
            context.set_code(grpc.StatusCode.ABORTED)
            return document_pb2.DeleteResponse(success=False, message='Document not Exist.')
        else: # 找到
            values = json.loads(values)
            redis_client.delete(request.document_id)
            self.executor.submit(update_hive, request.document_id, '', 'delete')
            return document_pb2.DeleteResponse(success=True, message='Document Delete.') 

    def ListDocuments(self, request, context):
        logger.info('Request to List Documents')
        keys = redis_client.keys('*')
        keys = [key for key in keys]
        print(keys)
        return document_pb2.ListResponse(success=True, message=keys)


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