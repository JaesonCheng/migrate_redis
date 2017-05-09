#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Date : 2017-05-09
# Author: JaesonCheng
# Version: 0.2

import datetime
import sys
try:
    import redis
except:
    print 'moudle redis not install , please run cmd "pip install redis" first.'
    sys.exit(1)
from multiprocessing.dummy import Pool as ThreadPool


def usage():

    print u'''
  Usage: 
      python %s SRC DEST [method]       同步源 Redis 所有 key 到目标 Redis 

      SRC     源 Redis 信息，包括 IP，PORT，DB，PASSWD ，用冒号做分割符
      DEST    目标 Redis 信息，包括 IP，PORT，DB，PASSWD ，用冒号做割符
      DB      默认选择 db 0
      
      method  取值为 1 或 2 
          1   默认值，单个 key 依次操作，速度较慢
          2   采用 redis pipeline 机制 , 同时多个 key 操作 ，速度较快
      
  example:
      1. python %s 192.168.1.1:4500 192.168.1.5:4500
      2. python %s 192.168.1.1:4500:0 192.168.1.5:4500:1
      3. python %s 192.168.1.1:4500 192.168.1.5:4500::passwd
      4. python %s 192.168.1.1:4501:0:passwd 192.168.1.5:4500:1:passwd 2
      ''' % (sys.argv[0],sys.argv[0],sys.argv[0],sys.argv[0],sys.argv[0])

            
class RedisMigrate():
    def __init__(self,sourceip,sourceport,sourcedb,sourcepasswd,targetip,targetport,targetdb,targetpasswd):
        self.sip = sourceip
        self.sport = sourceport
        self.sdb = sourcedb
        self.spasswd = sourcepasswd
        self.tip = targetip
        self.tport = targetport
        self.tdb = targetdb
        self.tpasswd = targetpasswd
        
        self.threadnumber = 20
        self.err_count = 0
        self.pipe_size = 1000

        try:
            src_conn = redis.ConnectionPool(host=self.sip, port=self.sport, db=self.sdb, password=self.spasswd)
            self.src_redis = redis.Redis(connection_pool=src_conn)
        except:
            print 'source redis can not connect'
            sys.exit(1)
        try:
            dst_conn = redis.ConnectionPool(host=self.tip, port=self.tport, db=self.tdb, password=self.tpasswd)
            self.dst_redis = redis.Redis(connection_pool=dst_conn)
        except:
            print 'target redis can not connect'
            sys.exit(1)
            
        self.src_pipe = self.src_redis.pipeline()
        self.dst_pipe = self.dst_redis.pipeline()
  
    def __len__(self):
        return self.src_redis.dbsize()

    def __memused__(self):
        return self.src_redis.info()['used_memory']

    def add_err_count(self):
        self.err_count = self.err_count + 1
        
    def flush_target(self):
        """Function to flush the target server."""
        try:
            self.dst_redis.flushdb()
            return 'flushdb(%s) ok' % self.tdb
        except:
            return 'flushdb(%s) fail' % self.tdb

    def base_restore(self,key):
        """获取 key 的 value ，然后写入目标redis"""
        try:
            value = self.src_redis.dump(key)
            kttl = self.src_redis.ttl(key)
            if kttl == -2:    ## key 已过期
                pass
            else:
                self.dst_redis.restore(key, 0, value)
                if kttl == -1:  ## key 永不过期
                    pass
                elif kttl == None:  ## 啥情况不清楚?
                    pass
                else:           ## update ttl
                    self.dst_redis.expire(key,kttl)
        except:
            self.add_err_count()


    def pipe_restore(self,key_list):
        """通过redis的pipeline机制，一次提交多个命令；获取key ttl value，并set到目标redis"""
        keyttlList = self.src_pipe.execute()
        for (k, v, t) in zip(key_list, keyttlList[0::2], keyttlList[1::2]):
            self.dst_pipe.set(k,v,ex=t)
        result = self.dst_pipe.execute()
        for (k, r) in zip(key_list, result):
            if not r:
                print "set %s fail." % k
                sys.exit(1)

        
    def migrate(self,method):
        if self.src_redis.dbsize() != 0:
            keys = self.src_redis.keys()
            if method == 1:   # 一次提交一个命令，多线程提交
                pool = ThreadPool(self.threadnumber)
                results = pool.map(self.base_restore,keys)
                pool.close()
                pool.join()
                
            if method == 2:   # 通过redis的pipeline机制，一次提交多个命令
                src_len = 0
                key_list = []
                for key in self.src_redis.keys():
                    key_list.append(key)
                    self.src_pipe.get(key)
                    self.src_pipe.pttl(key)
                    if src_len < self.pipe_size:
                        src_len += 1
                    else:
                        self.pipe_restore(key_list)
                        src_len = 0
                        key_list = []

                # 如果key列表里边有值
                if key_list:
                    self.pipe_restore(key_list)
        else:
            print 'source redis db is null'
            sys.exit()
    
        

if __name__ == "__main__":

    ###################################################################
    ###### 从脚本参数获取 redis 的 ip port db passwd 信息  ############
    src_ip,src_port,src_db,src_pass = None,6379,0,None
    dst_ip,dst_port,dst_db,dst_pass = None,6379,0,None
    method = 1

    if len(sys.argv) == 3 or len(sys.argv) == 4:
        src_list = map(str, sys.argv[1].split(':'))   # src 参数拆分
        if len(src_list) == 2:
            src_ip,src_port = str(src_list[0]),int(src_list[1])
        elif len(src_list) == 3:
            if src_list[2] == '':
                src_ip,src_port,src_db = str(src_list[0]),int(src_list[1]),0
            else:
                src_ip,src_port,src_db = str(src_list[0]),int(src_list[1]),int(src_list[2])
        elif len(src_list) == 4:
            if src_list[2] == '':
                src_ip,src_port,src_db,src_pass = str(src_list[0]),int(src_list[1]),0,str(src_list[3])
            else:
                src_ip,src_port,src_db,src_pass = str(src_list[0]),int(src_list[1]),int(src_list[2]),str(src_list[3])
        else:
            usage()
            sys.exit(1)
        dst_list = map(str, sys.argv[2].split(':'))    # dst 参数拆分
        if len(dst_list) == 2:
            dst_ip,dst_port = str(dst_list[0]),int(dst_list[1])
        elif len(dst_list) == 3:
            if dst_list[2] == '':
                dst_ip,dst_port,dst_db = str(dst_list[0]),int(dst_list[1]),0
            else:
                dst_ip,dst_port,dst_db = str(dst_list[0]),int(dst_list[1]),int(dst_list[2])
        elif len(dst_list) == 4:
            if dst_list[2] == '':
                dst_ip,dst_port,dst_db,dst_pass = str(dst_list[0]),int(dst_list[1]),0,str(dst_list[3])
            else:
                dst_ip,dst_port,dst_db,dst_pass = str(dst_list[0]),int(dst_list[1]),int(dst_list[2]),str(dst_list[3])
        else:
            usage()
            sys.exit(1)
        if len(sys.argv) == 4:                         # method 模式           
            if int(sys.argv[3]) == 1 or int(sys.argv[3]) == 2:
                method = int(sys.argv[3])
            else:
                usage()
                sys.exit(1)
    else:
        usage()
        sys.exit(1)

    if src_ip == None or src_ip == "" or dst_ip == None or dst_ip == "":
        usage()
        sys.exit(1)
    ######################## 获取参数，判断参数完毕 #####################
    #####################################################################

        
    ########################################################################   
    ## 开始同步 Redis 数据操作
    print '*' * 50
    time1 = datetime.datetime.now()

    mg = RedisMigrate(src_ip,src_port,src_db,src_pass,dst_ip,dst_port,dst_db,dst_pass)
    print "redis src total keys: %d  used memory: %d" % (mg.__len__(),mg.__memused__()/1024.0/1024.0)
    mg.migrate(method)
    print "redis dst total keys: %d " % mg.dst_redis.dbsize()

    time2 = datetime.datetime.now()
    print "err_count: %d \n" % mg.err_count
    print "Start at %s , End at %s , Usetime: %.3f s" % (time1.strftime("%Y-%m-%d %H:%M:%S"),time2.strftime("%Y-%m-%d %H:%M:%S"),(time2-time1).seconds)
    print '*' * 50
    ## 完成同步
    ########################################################################
