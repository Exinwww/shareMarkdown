from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, emit
import grpc
import document_pb2
import document_pb2_grpc
import eventlet
import logging
import threading
import queue
import multiprocessing
import asyncio
eventlet.monkey_patch()  # 进行猴子补丁

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")  # 使用eventlet作为异步模式
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 日志格式
    handlers=[
        logging.FileHandler("logs/app.flask_log"),  # 将日志输出到文件
        logging.StreamHandler()  # 将日志输出到控制台
    ]
)
logger = logging.getLogger(__name__)
# 当客户端连接时触发
# 当客户端断开连接时触发
# 广播消息给所有客户端

def get_document_stub():
    channel = grpc.insecure_channel('localhost:50051')
    stub = document_pb2_grpc.DocumentServiceStub(channel)
    return stub

async def get_async_document_stub():
    channel = grpc.aio.insecure_channel('localhost:50051')
    stub = document_pb2_grpc.DocumentServiceStub(channel)
    return stub

# 客户端连接与文档更新广播
def broadcast_message(document_id, message):
    logger.info('broadcast called.')
    print('#### broadcast ####')
    socketio.emit('broadcast_message', {'document_id':document_id,'message': message}, room=document_id)

@socketio.on('join_document')
def handle_join_document(data):
    document_id = data['document_id']
    join_room(document_id)
    print(f'Client joined document room {document_id}')

@socketio.on('leave_document')
def handle_leave_document(data):
    document_id = data['document_id']
    leave_room(document_id)
    print(f'Client left document room {document_id}')

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconect():
    print('Client disconnected')

@socketio.on('get')
def get_document(data):
    did = data['document_id']
    stub = get_document_stub()
    response = stub.ReadDocument(
        document_pb2.ReadRequest(document_id = str(did))
    )
    socketio.emit('get', {
        'content': response.content,
        'version': response.version
    })
    # return jsonify(type='get', content=response.content, version = response.version)
# @socketio.on('save')
# def save_document(data):
#     did = data['document_id']
#     content = data['content']
#     version = data['version']
#     stub = get_document_stub()
#     response = stub.WriteDocument(document_pb2.WriteRequest(
#         document_id = str(did), content =  content, version = version
#     ))
#     # socketio.emit('save', {
#     #     'success':response.success,
#     #     'message':response.message
#     # })
#     if response.success:
#         broadcast_message(did, f"Document {did} has been updated.") #
@socketio.on('save')
def save_document(data):
    save_queue.put(data)
    logger.info('main thread finished save_document')
    socketio.emit('save', {
        'success':'True',
        'message':'nihao'
    })

# async def async_write_document(stub, document_id, content, version):
#     response = await stub.WriteDocument(document_pb2.WriteRequest(
#         document_id=str(document_id), content=content, version=version
#     ))
#     return response

# async def save_document_worker(save_queue):
#     logger.info('save_document_worker START')
#     while True:
#         logger.info('save_document_worker Running')
#         data = save_queue.get()
#         if data is None:  # 用于停止线程的信号
#             break
#         logger.info(f"Processing save for document_id {data['document_id']}")
#         try:
#             did = data['document_id']
#             content = data['content']
#             version = data['version']
#             stub = await get_async_document_stub()
#             response = await async_write_document(stub, did, content, version)
#             if response.success:
#                 broadcast_message(did, f"Document {did} has been updated.")
#             # 通知客户端保存结果
#             socketio.emit('save_response', {
#                 'success': response.success,
#                 'message': response.message
#             }, room=data['sid'])  # 使用session id来指定返回给哪个客户端
#         except Exception as e:
#             logger.error(f"Error processing save for document_id {data['document_id']}: {e}")

########## 多进程
def write_document(stub, document_id, content, version):
    response = stub.WriteDocument(document_pb2.WriteRequest(
        document_id=str(document_id), content=content, version=version
    ))
    return response
def save_document_worker(save_queue):
    logger.info('save_document_worker START')
    while True:
        logger.info('save_document_worker Running')
        data = save_queue.get()
        if data is None:  # 用于停止线程的信号
            break
        logger.info(f"Processing save for document_id {data['document_id']}")
        try:
            did = data['document_id']
            content = data['content']
            version = data['version']
            stub = get_document_stub()
            response = write_document(stub, did, content, version)
            if response.success:
                broadcast_message(did, f"Document {did} has been updated.")
            # 通知客户端保存结果
            socketio.emit('save_response', {
                'success': response.success,
                'message': response.message
            }, room=did)  # 使用session id来指定返回给哪个客户端
        except Exception as e:
            logger.error(f"Error processing save for document_id {data['document_id']}: {e}")

@socketio.on('create')
def create_document(data):
    did = data['document_id']
    stub = get_document_stub()
    response = stub.CreateDocument(document_pb2.CreateRequest(
        document_id = str(did)
    ))
    socketio.emit('create', {
        'success':response.success,
        'message':response.message
    })
    # return jsonify(type='create',success=response.success, message=response.message)
@socketio.on('delete')
def delete_document(data):
    did = data['document_id']
    stub = get_document_stub()
    response = stub.DeleteDocument(document_pb2.DeleteRequest(
        document_id = str(did)
    ))
    if response.success:
        broadcast_message(document_id, f"Document {did} has been deleted.") # need to modify
    socketio.emit('delete', {
        'success':response.success,
        'message':response.message
    })
    # return jsonify(type='delete', success=response.success, message=response.message)
@socketio.on('list')
def get_document_list():
    stub = get_document_stub()
    response = stub.ListDocuments(document_pb2.Empty())
    socketio.emit('list', {
        'success':response.success,
        'message':list(response.message)
    })

if __name__ == '__main__':
    # save_queue = queue.Queue()
    # save_thread = threading.Thread(target=save_document_worker, args=(save_queue,))
    # save_thread.start()
    # asyncio.run(save_document_worker(save_queue))

    save_queue =  multiprocessing.Queue()
    save_thread = multiprocessing.Process(target=save_document_worker, args=(save_queue,))
    save_thread.start()
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=5678)
    finally:
        save_queue.put(None) # 发送停止信号
        save_thread.join()
    # app.run(debug=True, host='localhost', port = 5000)
    # socketio.run(app, debug=True, host='0.0.0.0', port=5678)