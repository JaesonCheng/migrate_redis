#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Date : 2017-09-12
# Author: JaesonCheng
# Version: 0.3.1

import datetime
import sys
try:
    import redis
except:
    print 'moudle redis not install , please run cmd "pip install redis" first.'
    sys.exit(1)


def usage():

    print u'''
  Usage: 
      python %s SRC DEST        同步源 Redis 所有 key 到目标 Redis 

      SRC     源 Redis 信息，包括 IP，PORT，DB，PASSWD ，用冒号做分割符
      DEST    目标 Redis 信息，包括 IP，PORT，DB，PASSWD ，用冒号做分割符
      DB      默认选择 db 0
      
  example:
      1. python %s 192.168.1.1:4500 192.168.1.5:4500
      2. python %s 192.168.1.1:4500:0 192.168.1.5:4500:1
      3. python %s 192.168.1.1:4500:1 192.168.1.5:4500::passwd
      4. python %s 192.168.1.1:4501:0:passwd 192.168.1.5:4500:1:passwd
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
        
        self.valuenil = 0        # 取出来的 value 为空时 +1
        self.keyexist = 0        # key 在 目标 redis 中存在时 +1
        self.koverdue = 0        # key 已过期时 +1
        self.pipesize = 1000     # 建议源为线上业务时，值不要超过1000， pipeline 方式会能 redis 产生阻断，影响线上 redis 正常请求。

        try:
            src_conn = redis.ConnectionPool(host=self.sip, port=self.sport, db=self.sdb, password=self.spasswd)
            self.src_redis = redis.Redis(connection_pool=src_conn)
            self.src_pipe = self.src_redis.pipeline()
            test1 = self.src_redis.dbsize()
        except:
            print 'source redis can not connect'
            sys.exit(1)
        try:
            dst_conn = redis.ConnectionPool(host=self.tip, port=self.tport, db=self.tdb, password=self.tpasswd)
            self.dst_redis = redis.Redis(connection_pool=dst_conn)
            self.dst_pipe = self.dst_redis.pipeline()
            test2 = self.dst_redis.dbsize()
        except:
            print 'target redis can not connect'
            sys.exit(1)
  
    def __len__(self):
        return [self.src_redis.dbsize(), self.dst_redis.dbsize()]

    def __memused__(self):
        return [self.src_redis.info()['used_memory'], self.dst_redis.info()['used_memory']]

    def addvaluenil(self):
        self.valuenil = self.valuenil + 1
        
    def addkeyoverdue(self):
        self.koverdue = self.koverdue + 1

    def addkeyexist(self):
        self.keyexist = self.keyexist + 1

    def checkeyexist(self):
        exkeyList = []
        i = -1
        srckeys = self.src_redis.keys()
        for key in srckeys:
            self.dst_pipe.exists(key)
        for st in self.dst_pipe.execute():
            i = i + 1    # 获取索引
            if st:
                self.addkeyexist()
                exkeyList.append(srckeys[i])
        return exkeyList
            
    def pipe_restore(self,keys):
        src_len = 0
        keylist = []
        for key in keys:
            keylist.append(key)
            self.src_pipe.dump(key)
            self.src_pipe.ttl(key)
            if src_len < self.pipesize:
                src_len += 1
            else:
                keyttlList = self.src_pipe.execute()
                for (k, t, v) in zip(keylist, keyttlList[1::2], keyttlList[0::2]):
                    if t == None or t == -1:
                        if v != None:
                            self.dst_pipe.restore(k,0,v)
                        else:
                            self.addvaluenil()
                    elif t == -2:
                        self.addkeyoverdue()
                    else:
                        if v != None:
                            #print "debug1: k=%s, t=%d, type(t)=%s" % (k, t, type(t))
                            self.dst_pipe.restore(k,t*1000,v)
                        else:
                            self.addvaluenil()
                self.dst_pipe.execute()
                src_len = 0
                keylist = []
        if keylist:    # 如果key列表里边有值
            keyttlList = self.src_pipe.execute()
            for (k, t, v) in zip(keylist, keyttlList[1::2], keyttlList[0::2]):
                if t == None or t == -1:
                    if v != None:
                        self.dst_pipe.restore(k,0,v)
                    else:
                        self.addvaluenil()
                elif t == -2:
                    self.addkeyoverdue()
                else:
                    if v != None:
                        #print "debug1: k=%s, t=%d, type(t)=%s" % (k, t, type(t))
                        self.dst_pipe.restore(k,t*1000,v)
                    else:
                        self.addvaluenil()
            self.dst_pipe.execute()
        
    def migrate(self):
        if self.src_redis.dbsize() != 0:
            keys = self.src_redis.keys()
            exkeylist = self.checkeyexist()
            if self.keyexist == 0:
                self.pipe_restore(keys)
            elif self.keyexist > 0 and self.keyexist <= 50:
                print exkeylist
                for kk in exkeylist:
                    keys.remove(kk)
                self.pipe_restore(keys)
                print "\nskip key : %d " % self.keyexist
            else:
                print "\nexist key in target redis : %d " % self.keyexist
                print "sys.exit()"
                print '*' * 60
                sys.exit()
                
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
    print '*' * 60
    time1 = datetime.datetime.now()

    r = RedisMigrate(src_ip,src_port,src_db,src_pass,dst_ip,dst_port,dst_db,dst_pass)
    print "redis src total keys: %d  used memory: %d Mb" % (r.__len__()[0], r.__memused__()[0]/1024.0/1024.0)
    r.migrate()
    print "redis dst total keys: %d \n" % r.__len__()[1]

    time2 = datetime.datetime.now()
    print "value is nil: %d " % r.valuenil
    print "key overdue : %d " % r.koverdue
    print "key is exist: %d \n" % r.keyexist
    print "Start at %s , End at %s , Usetime: %.3f s" % (time1.strftime("%Y-%m-%d %H:%M:%S"),time2.strftime("%Y-%m-%d %H:%M:%S"),(time2-time1).seconds)
    print '*' * 60
    ## 完成同步
    ########################################################################
