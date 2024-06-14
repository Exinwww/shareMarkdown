echo "关闭HDFS"
stop-dfs.sh

echo "关闭YARN"
stop-yarn.sh


stop_service() {
  local service_name=$1
  local service_pid

  # Find the PID of the service
  service_pid=$(ps aux | grep $service_name | grep -v grep | awk '{print $2}')
  
  if [ -n "$service_pid" ]; then
    echo "Stopping $service_name process with PID $service_pid"
    kill -9 $service_pid
    echo "$service_name stopped."
  else
    echo "No $service_name process found."
  fi
}

# Stop HiveServer2
stop_service HiveServer2

# Stop MetaStore
stop_service MetaStore


echo "分别关闭ZooKeeper"
# ssh到节点，并按照ZooKeeper路径，开启zookeeper服务
# 注意需要修改为自己的节点名及安装路径
echo "Stoping ZooKeeper of node1"
ssh -t node1 << 'EOF'
/export/server/zookeeper/bin/zkServer.sh stop
EOF

echo "Stoping ZooKeeper of node2"
ssh -t node2 << 'EOF'
/export/server/zookeeper/bin/zkServer.sh stop
EOF

echo "Stoping ZooKeeper of node3"
ssh -t node3 << 'EOF'
/export/server/zookeeper/bin/zkServer.sh stop
EOF