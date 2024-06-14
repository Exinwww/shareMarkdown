echo "启动HDFS"
start-dfs.sh

echo "启动YARN"
start-yarn.sh

echo "启动元数据管理服务"
cd /export/server/hive
nohup bin/hive --service metastore >> logs/metastore.log 2>&1 &
nohup bin/hive --service hiveserver2 >> logs/hiveserver2.log 2>&1 &


echo "分别启动ZooKeeper"
# ssh到节点，并按照ZooKeeper路径，开启zookeeper服务
# 注意需要修改为自己的节点名及安装路径
echo "Strating ZooKeeper of node1"
ssh -t node1 << 'EOF'
/export/server/zookeeper/bin/zkServer.sh start
EOF

echo "Strating ZooKeeper of node2"
ssh -t node2 << 'EOF'
/export/server/zookeeper/bin/zkServer.sh start
EOF

echo "Strating ZooKeeper of node3"
ssh -t node3 << 'EOF'
/export/server/zookeeper/bin/zkServer.sh start
EOF