# pythonscripts

    Author: JaesonCheng

## migrate_redis.py

### help

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

### migrate

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
