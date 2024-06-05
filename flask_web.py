from flask import Flask, request, jsonify
import grpc
import document_pb2
import document_pb2_grpc

app = Flask(__name__)

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
    print(f"Document ID: {document_id}, Content: {content}, Version: {version}")  # Debug output
    stub = get_document_stub()
    response = stub.WriteDocument(document_pb2.WriteRequest(
        document_id=str(document_id), content=content, version=version)
    )
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
    return jsonify(success=response.success, message=response.message)

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port = 5000)