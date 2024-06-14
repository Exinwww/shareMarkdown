// const io = require('socket.io-client');
document.addEventListener('DOMContentLoaded', function () {
    let saveNotification = {}; // 写操作通知栏
    let createNotification = {}; // 新建操作通知栏
    let in_room = "None";
    let version = 'v0';
    const socket = io('http://192.168.88.101:5678',{
        transports: ['websocket'], // 优先使用 WebSocket
        timeout: 10*60000,  // 设置连接超时时间为120秒（2分钟）
        pingInterval: 10*60000, // 心跳间隔，单位为毫秒
        pingTimeout: 10*60000, // 心跳超时，单位为毫秒
    });
    

    const editor = document.getElementById('editor_div');
    const md_input = document.getElementById('markdown-input');
    const preview = document.getElementById('preview_div');

    // 实时预览
    editor.addEventListener('input', function () {
        const markdown = md_input.value;
        const html = marked.parse(markdown);
        preview.innerHTML = html;
    });
    
    // button的点击事件绑定
    document.getElementById('new').addEventListener('click', function () {
        console.log('button of new was clicked');
        newInput();
    });
    document.getElementById('save').addEventListener('click', function () {
        console.log('button of save was clicked');
        if(in_room != "None"){
            socket.emit('save', {'document_id': in_room, 'content': md_input.value, 'version':version});
            // 通知栏保持显示，指示保存操作正在进行。
            saveNotification[in_room] = Swal.fire({
                title: String(in_room) +' is saving...',
                text: 'This notification will stay open until manually closed.',
                showConfirmButton: false,
                toast: true,
                position: 'top-end',
                timerProgressBar: true,
                // onClose: () => {
                //     // Perform any action when the notification is closed
                //     console.log('Persistent notification closed.');
                // }
            });
        }else{
            console.log('in_room is None');
        }
    });
    document.getElementById('export').addEventListener('click', function () {
        console.log('button of export was clicked');
        exportOperation();
    });
    document.getElementById('flush').addEventListener('mousedown', function () {
        console.log('button of flush was clicked');
        socket.emit('list');
    });

    socket.addEventListener('list', function (data) {
        console.log('get sth on list.')
        console.log(data);
        const file_name_list = data.message;
        if(file_name_list.length != 0){
            document.getElementById('file_name_select').innerHTML = '';
        }else{
            const option = document.createElement('option');
            option.value = 'None';
            option.innerHTML = 'None';
            document.getElementById('file_name_select').appendChild(option);
            return;
        }
        file_name_list.forEach(function (file_name) {
            const option = document.createElement('option');
            option.value = file_name;
            option.innerHTML = file_name;
            document.getElementById('file_name_select').appendChild(option);
        });
        
        // 设置下拉框的监听事件，选择该选项则会触发socket事件get
        let selectDom = document.getElementById('file_name_select');
        selectDom.onchange = function() {
            let index = this.options.selectedIndex;
            let value = this.options[index].value;
            console.log(value);
            if(value != 'None'){
                if(in_room != "None"){
                    socket.emit('leave_document', {'document_id': in_room});
                }
                in_room = value;
                socket.emit('join_document', {'document_id': value});
                socket.emit('get', {'document_id': value});
            }
        }
        if(file_name_list.length != 0){
            if(in_room == "None"){
                selectDom.value = file_name_list[0];
            }else{
                selectDom.value = in_room;
            }
            var event = new Event('change');
            selectDom.dispatchEvent(event);
        }
        listNotice();
    });
    socket.addEventListener('get', function(data){
        console.log(data);
        md_input.value = data.content;
        version = data.version;
        const html = marked.parse(data.content);
        preview.innerHTML = html;
    });
    socket.addEventListener('save', function(data){
        console.log(data);
        let did = data['document_id'];
        if(data['success'] == true){
            // 关闭保存中的通知栏
           saveNotification[did].close();
           // 显示保存成功的通知栏
           Swal.fire({
            title: String(did) + ' save success!',
            // text: 'This will close in 3 seconds.',
            timer: 3000, // Auto close after 3 seconds
            timerProgressBar: true,
            showConfirmButton: false,
            toast: true,
            position: 'top-end'
        });
        }else{
            // 关闭保存中的通知栏
            saveNotification[did].close();
            // 显示保存失败的通知栏
            Swal.fire({
                title: String(did) + ' save failed!',
                // text: 'This will close in 3 seconds.',
                timer: 3000, // Auto close after 3 seconds
                timerProgressBar: true,
                showConfirmButton: false,
                toast: true,
                position: 'top-end'
            });
        }
    });
    socket.addEventListener('delete', function(data){
        console.log(data);
    });
    socket.on('create', function(data){     
        console.log('get sth on create.')
        console.log(data);
        let did = data['document_id'];
        if(data['success']){
            // 关闭新建中的通知栏
            createNotification[did].close();
            // 显示新建成功的通知栏
            Swal.fire({
                title: String(did) + ' create success!',
                // text: 'This will close in 3 seconds.',
                timer: 3000, // Auto close after 3 seconds
                timerProgressBar: true,
                showConfirmButton: false,
                toast: true,
                position: 'top-end'
            });
        }else{
             // 关闭新建中的通知栏
             createNotification[did].close();
             // 显示新建失败的通知栏
                Swal.fire({
                    title: String(did) + ' create failed!',
                    // text: 'This will close in 3 seconds.',
                    timer: 3000, // Auto close after 3 seconds
                    timerProgressBar: true,
                    showConfirmButton: false,
                    toast: true,
                    position: 'top-end'
                });
        }
    });
    socket.addEventListener('broadcast_message', function(data){
        console.log(data);
        if(data['document_id'] == in_room){
            Swal.fire({
                title: String(in_room) + ' has been changed!',
                // text: 'This will close in 3 seconds.',
                timer: 3000, // Auto close after 3 seconds
                timerProgressBar: true,
                showConfirmButton: false,
                toast: true,
                position: 'top-end'
            });
            // 更新文档内容
            md_input.value = data['message'];
            version = data['version'];
            const html = marked.parse(data['message']);
            preview.innerHTML = html;
        }
    });
    


    socket.on('connect', () => {
        console.log('Connected to server');
      });
      
    socket.on('disconnect', (reason) => {
        console.log('Disconnected from server. Reason:', reason);
      });
      
      socket.on('reconnect_attempt', (attemptNumber) => {
        console.log('Reconnect attempt:', attemptNumber);
      });
      
      socket.on('reconnect_error', (error) => {
        console.log('Reconnect error:', error);
      });
      
      socket.on('reconnect_failed', () => {
        console.log('Reconnect failed');
      });
      // 新建操作
      function newInput(){
        let did;
        Swal.fire({
            title: 'New File',
            input:'text',
            inputLabel: 'File Name',
            showCancelButton: true,
            confirmButtonText: 'Create',
            cancelButtonText: 'Cancel'
        }).then((result) => {
            if(result.value){
                did = result.value;
                Swal.fire('File Name: ' + result.value)
                socket.emit('create', {'document_id': result.value});
                showCreateNotification(did);
            }
        });
        
      }
      function showCreateNotification(did){
        createNotification[did] = Swal.fire({
            title: String(did) +' is creating...',
            text: 'This notification will stay open until manually closed.',
            showConfirmButton: false,
            toast: true,
            position: 'top-end',
            timerProgressBar: true,
            customClass: {
                popup: 'my-swal'
              }
            // onClose: () => {
            //     // Perform any action when the notification is closed
            //     console.log('Persistent notification closed.');
            // }
        });
      }
      // 导出操作
      function exportOperation(){
        Swal.fire({
            title: 'This Op is not implemented yet',
            inputLabel: 'File Name',
            // showCancelButton: true,
            // cancelButtonText: 'Cancel'
        })
      }
      // list 通知栏
      function listNotice(){
        Swal.fire({
            title: 'Got Documents List',
            // text: 'This will close in 3 seconds.',
            timer: 3000, // Auto close after 3 seconds
            timerProgressBar: true,
            showConfirmButton: false,
            toast: true,
            position: 'top-end'
        });
      }

      // 写操作
});

// socket.emit('join_document', {'document_id':'233'});