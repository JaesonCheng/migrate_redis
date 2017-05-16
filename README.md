# migrate_redis.py

    Author: JaesonCheng

## 说明

如果同步redis数据时，源redis和目标redis是一对一的关系，那么直接使用官方的 slaveof 命令做主从即可。

如果你需要把多个redis数据同步到一个redis里面，那么你不得不自己写脚本程序来实现从源redis读取数据，然后再写入目标redis中。本脚本就是用来干这事的。

### 帮助

    [root@itdhz JaesonCheng]# python migrate_redis.py

      Usage: 
          python migrate_redis.py SRC DEST [method]       同步源 Redis 所有 key 到目标 Redis 

          SRC     源 Redis 信息，包括 IP，PORT，DB，PASSWD ，用冒号做分隔符
          DEST    目标 Redis 信息，包括 IP，PORT，DB，PASSWD ，用冒号做隔符
          PORT    默认值 6379
          DB      默认值 0

      example:
          1. python migrate_redis.py 192.168.1.1:4500 192.168.1.5:4500
          2. python migrate_redis.py 192.168.1.1:4500:0 192.168.1.5:4500:1
          3. python migrate_redis.py 192.168.1.1:4500 192.168.1.5:4500::passwd
          4. python migrate_redis.py 192.168.1.1:4501:0:passwd 192.168.1.5:4500:1:passwd

支持 源redis 、 目标redis 两个参数，

其中， 源redis 和 目标redis 可以带4个域(ip,port,db,passwd)，分别用冒号分隔开， 

其中， port 有默认值 6379 ， db 有默认值 0 ， 有默认值的情况下此域可以不写，但域之间的分隔符不可少。

例如，将 ip=192.168.1.1 , port=6379 , db=0 , passwd='test123' 的源redis 的数据同步到 ip=192.168.1.5 , port=6379 , db=3, passwd=‘’ 的目标 redis上，可以如下写

    python migrate_redis.py 192.168.1.1:::test123 192.168.1.5::3


### redis数据同步

    [root@itdhz ~]# python migrate_redis.py 127.0.0.1:6379:0 127.0.0.1:7000:0:test123
    ************************************************************
    redis src total keys: 73271  used memory: 7 Mb
    redis dst total keys: 73271 

    value is nil: 0 
    key overdue : 0 
    key is exist: 0 

    Start at 2017-05-16 13:55:01 , End at 2017-05-16 13:55:07 , Usetime: 6.000 s
    ************************************************************
    [root@itdhz ~]# python migrate_redis.py 127.0.0.1:6379:0 127.0.0.1:7000:0:test123
    ************************************************************
    redis src total keys: 73271  used memory: 7 Mb

    exist key in target redis : 73271 
    sys.exit()
    ************************************************************
    [root@itdhz ~]# 

第一次能正常同步，第二次同步时因为目标redis已经存在了相同的key，发生冲突，所以提示并退出。

### 不同区域防火墙转发设置

例如

    source redis ： 111.222.333.444（外网） 192.168.1.5（内网）， redis启动时监听内网 3679 端口  
    target redis ： 555.666.777.888（外网） 192.168.2.5（内网）， redis启动时监听内网 3680 端口  

如果这两个 redis 不在同一个内网，要把 source redis 的数据同步到 target redis 上，就需要做防火墙转发设置。  

在 source redis 上做以下设置

    [root@source ~]# iptables -A INPUT -s 555.666.777.888/32 -p tcp -m tcp --dport 3679 -j ACCEPT
    [root@source ~]# iptables -t nat -A PREROUTING -d 111.222.333.444/32 -p tcp -m tcp --dport 3679 -j DNAT --to-destination 192.168.1.5
    [root@source ~]# iptables -t nat -A POSTROUTING -d 192.168.1.5/32 -p tcp -m tcp --dport 3679 -o eth1 -j MASQUERADE

然后，就可以在 target 机器上运行脚本  

    [root@target ~]# python migrate_redis.py 111.222.333.444:3679 192.168.2.5:3680    

## other

暂无
