# pythonscripts

    Author: JaesonCheng

## migrate_redis.py

### 帮助

    [root@itdhz JaesonCheng]# python migrate_redis.py

      Usage: 
          python migrate_redis.py SRC DEST [method]       同步源 Redis 所有 key 到目标 Redis 

          SRC     源 Redis 信息，包括 IP，PORT，DB，PASSWD ，用冒号做分割符
          DEST    目标 Redis 信息，包括 IP，PORT，DB，PASSWD ，用冒号做割符
          DB      默认选择 db 0
          
          method  取值为 1 或 2 
              1   默认值，单个 key 依次操作，速度较慢
              2   采用 redis pipeline 机制 , 同时多个 key 操作 ，速度较快
          
      example:
          1. python migrate_redis.py 192.168.1.1:4500 192.168.1.5:4500
          2. python migrate_redis.py 192.168.1.1:4500:0 192.168.1.5:4500:1
          3. python migrate_redis.py 192.168.1.1:4500 192.168.1.5:4500::passwd
          4. python migrate_redis.py 192.168.1.1:4501:0:passwd 192.168.1.5:4500:1:passwd 2

### redis数据同步

    [root@itdhz JaesonCheng]# python migrate_redis.py 127.0.0.1:6379 127.0.0.1:6380
    **************************************************
    redis src total keys: 100457  used memory: 10 Mb
    redis dst total keys: 100457 
    err_count: 1002 

    Start at 2017-05-09 13:46:50 , End at 2017-05-09 13:47:24 , Usetime: 34.000 s
    **************************************************
    [root@itdhz JaesonCheng]# python migrate_redis.py 127.0.0.1:6379 127.0.0.1:6380 2
    **************************************************
    redis src total keys: 100457  used memory: 10 Mb
    redis dst total keys: 100457 
    err_count: 0 

    Start at 2017-05-09 13:47:30 , End at 2017-05-09 13:47:40 , Usetime: 10.000 s
    **************************************************

### 不同区域防火墙转发设置

例如：
    source redis ： 111.222.333.444（外网） 192.168.1.5（内网）， redis启动时监听内网 3679 端口
    target redis ： 555.666.777.888（外网） 192.168.2.5（内网）， redis启动时监听内网 3680 端口

如果这两个 redis 不在同一个内网，要把 source redis 的数据同步到 target redis 上，就需要做防火墙转发设置。

在 source redis 上做以下设置

    [root@source ~]# iptables -A INPUT -s 555.666.777.888/32 -p tcp -m tcp --dport 3679 -j ACCEPT
    [root@source ~]# iptables -t nat -A PREROUTING -d 111.222.333.444/32 -p tcp -m tcp --dport 3679 -j DNAT --to-destination 192.168.1.5
    [root@source ~]# iptables -t nat -A POSTROUTING -d 192.168.1.5/32 -p tcp -m tcp --dport 3679 -o eth1 -j MASQUERADE
    
然后，就可以在 target 机器上运行脚本

    [root@target ~]# python migrate_redis.py 111.222.333.444:3679 555.666.777.888:3680
