from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, emit
import grpc
import document_pb2
import document_pb2_grpc
import eventlet
import logging
import threading
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

# 获取用户标识的函数
def get_user_identity():
    # e.g. curl -X GET -H "Authorization: Bearer your_token_here" http://localhost:5000/api/documents/testdoc1
    # 在这里你可以解析请求中的认证信息，比如令牌、用户名密码等
    # 这里以获取Authorization头部中的认证信息为例，你可以根据你的需求进行调整
    auth_header = request.headers.get('Authorization')
    if auth_header:
        # 在这里解析认证信息，比如从认证头部中提取出令牌或用户名密码
        # 假设认证信息格式为：Bearer <token>，或者 Basic <username:password>
        # 这里简单示范获取令牌
        _, token = auth_header.split(' ')
        return token
    return None


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
@socketio.on('save')
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
def save_document(data):
    def handle_save(data):
        did = data['document_id']
        content = data['content']
        version = data['version']
        logging.info(f"Received save request for document {did} with version {version}")

        stub = get_document_stub()
        try:
            response = stub.WriteDocument(document_pb2.WriteRequest(
                document_id = str(did), content =  content, version = version
            ))
            logging.info(f"RPC response: success={response.success}, message={response.message}")
        except Exception as e:
            logging.error(f"Error during RPC call: {str(e)}")
            socketio.emit('save', {
                'success': False,
                'message': str(e)
            })
            return

        if response.success:
            logging.info(f"Broadcasting message for document {did}")
            broadcast_message(did, f"Document {did} has been updated.")
        else:
            logging.info(f"Failed to save document {did}: {response.message}")
            socketio.emit('save', {
                'success': response.success,
                'message': response.message
            })

    eventlet.spawn(handle_save, data)
    
    
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
    # app.run(debug=True, host='localhost', port = 5000)
    socketio.run(app, debug=True, host='0.0.0.0', port=5678)