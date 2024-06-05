from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, emit
import grpc
import document_pb2
import document_pb2_grpc
import eventlet
import logging
eventlet.monkey_patch()  # 进行猴子补丁

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')  # 使用eventlet作为异步模式
logging.basicConfig(level=logging.DEBUG)
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

# GET命令，用于获取文档
@app.route('/api/documents/<document_id>', methods = ['GET'])
def get_document(document_id):
    stub = get_document_stub()
    response = stub.ReadDocument(
        document_pb2.ReadRequest(document_id=str(document_id))
    )
    return jsonify(content=response.content, version = response.version)
# POST命令，用于保存文档
@app.route('/api/documents/<document_id>', methods=['POST'])
def save_document(document_id):
    data = request.get_json()
    content = data['content']
    version = data['version']
    response = stub.WriteDocument(document_pb2.WriteRequest(
        document_id=str(document_id), content=content, version=version)
    )
    if response.success:
        broadcast_message(document_id, f"Document {document_id} has been updated.") # need to modify
    return jsonify(success=response.success, message=response.message)
# PUT命令，用于创建文档
@app.route('/api/documents/<document_id>', methods=['PUT'])
def create_document(document_id):
    stub = get_document_stub()
    response = stub.CreateDocument(document_pb2.CreateRequest(
        document_id=str(document_id))
    )
    return jsonify(success=response.success, message=response.message)
# DELETE命令，用于删除文档
@app.route('/api/documents/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    stub = get_document_stub()
    response = stub.DeleteDocument(document_pb2.DeleteRequest(
        document_id=str(document_id))
    )
    if response.success:
        broadcast_message(document_id, f"Document {document_id} has been deleted.") # need to modify
    return jsonify(success=response.success, message=response.message)

# 客户端连接与文档更新广播
def broadcast_message(document_id, message):
    socketio.emit('broadcast_message', {'message': message}, room=document_id)

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


if __name__ == '__main__':
    # app.run(debug=True, host='localhost', port = 5000)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)