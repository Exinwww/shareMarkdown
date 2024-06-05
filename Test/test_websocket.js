// 引入Socket.IO库
const io = require('socket.io-client');

// 连接到服务器
const socket = io('http://192.168.88.101:5000');

// 发送消息
socket.emit('join_document', {'document_id':'233'});

socket.emit('leave_document',  {'document_id':'233'});

// 监听服务器的响应消息
socket.on('response', (data) => {
    console.log('Server response:', data);
});
