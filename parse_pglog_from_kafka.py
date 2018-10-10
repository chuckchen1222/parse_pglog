#!//usr/bin/python
# coding:utf-8

# Purpose: This script is to monitor the database logs, count error messages, and send error messages to dbops.
# Author: chuckchen1222@gmail.com
# Date: 2018-06-06

from kafka import KafkaConsumer
from kafka import TopicPartition
import sys
import time
import json
import re
import psycopg2
from send_err_mail_pf import send_mail
import multiprocessing
import logging

KAFKA_LIST = ["kafka01:9092,kafka02:9092"]
CLIENT_ID = "parse_pglog" ##" % time.time()
DATABASE_NAME = ''
HOST = ''
PORT = ''
USER_NAME = ''
PASSWORD = ''
CHAR_SET = ''

# send mail to dbops
dbops = ['chuckchen1222@gmail.com']

def db_init():
    global DATABASE_NAME
    DATABASE_NAME = 'errlog'
    global HOST
    HOST = '192.168.1.101'
    global PORT
    PORT = '5432'
    global USER_NAME
    USER_NAME = 'dbadmin'
    global password
    pssword = ''
    global CHAR_SET
    CHAR_SET = 'utf8'

# conn log_parse
def get_dbops_conn():
    db_init()
    return psycopg2.connect(host = HOST, database = DATABASE_NAME, user = USER_NAME, password = PASSWORD, port = PORT)

def get_cursor(conn):
    return conn.cursor()

# close connect
def conn_close(conn):
    if conn != None:
        conn.close()

# close cursor
def cursor_close(cursor):
    if cursor != None:
        cursor.close()

# close all
def close(cursor, conn):
    cursor_close(cursor)
    conn_close(conn)

# usage
def Usage():
    if len(sys.argv) < 2:
        print('Usage: python %s <topic_name>' % sys.argv[0])
        print('       e.g: python %s test_data' % sys.argv[0])
        sys.exit(1)

# get the message of topic from kafka, return all_data
# client_id = zc_time
def get_data_kafka():
    KAFKA_LIST = ["kafka01:9092","kafka02:9092"]
    topic_name = "pglog" # sys.argv[1]
    client_id = "parse_dbwtest03ac" ##%s" % time.time()
    consumer = KafkaConsumer(topic_name, bootstrap_servers=KAFKA_LIST, client_id=client_id, group_id=client_id, auto_offset_reset="earliest")
    while True:
        for data in consumer:
            yield data.value
    print "get kafka data while end!"

# parse msg.value from get_data_kafka, and find the message.
# return error meesage
# data_v are from kafka data.
def find_err_message(data_v):
    main_errors = ['WARNING:', 'ERROR:', 'FATAL:', 'PANIC:']
    # exclude errors.
    exclude_errors = ['canceling statement due to statement timeout', 'recovery is in progress']
    j_data = json.loads(data_v)
    message = j_data.get("message")
    if any(err in message for err in main_errors):
        if not any(ex_err in message for ex_err in exclude_errors):
            return data_v

# get hostname from data
def get_host(err_data_v):
    j_data = json.loads(err_data_v)
    hostname = j_data['beat']['hostname']
    return hostname

# match message to tuple
# return match message
def match_msg(err_data_v):
    for data in err_data_v:
        j_data = json.loads(err_data_v)
        err_msg = j_data.get("message")
        # log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d %h
        c_msg = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\S*\s*\d* (\w{3}) (\[\d+\]): (\[\d+-\d+\]) user=(\S*\w*).\s*\S*db=(\S*\w*) ([a-zA-Z0-9\-\.]+|\[local\]|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[0-9a-fA-F:]+)?[:\d]* (LOG|WARNING|ERROR|FATAL|PANIC)?[:\d]*  (.*)'
        regex = re.compile(c_msg)
        msg = regex.match(err_msg)
        if msg:
            return msg.groups()

# open file to append data return 
def open_file_for_a(file):
    return open(file, 'a')

# close_file 
# fo = append_file(file)
# close_file(fo)
def close_file(file):
    return file.close()

# insert into file
# fo = append_file(file)
# insert_err_to_file(fo, msg)
def insert_err_to_file(fo,hostname,err_msg):
    fo.write('\n %s : %s '  % (hostname ,err_msg))
    fo.write('\n*******************************')

def comput_pgerr_times(connect,err_date,hostname,err_log):
    err_times_sql = '''select count(1) from t_db_err_log 
            where hostname = \'%s\'
            and err_log = \'%s\'
            and to_char(err_date,\'yyyy-mm-dd\') = \'%s\'
            ''' % (hostname, err_log, err_date)
    cursor_err_times_sql = get_cursor(connect)
    try:
        execute_comput = cursor_err_times_sql.execute(err_times_sql)
        result = cursor_err_times_sql.fetchone()
    except Exception,e:
        result = [0]
    finally:
        return result

# x = comput_pgerr_times(connect,err_date,hostname,err_msg)
# if x:
#     upsert_pgerr_send(connect,err_date,hostname,err_msg,result)
#
def upsert_pgerr_send(connect, err_date, hostname, err_log, result, db_name, client_addr):
    in_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    insert_err_send_sql = ''' insert into t_db_err_send (err_date, hostname, err_count, err_log, is_sent, sent_times, is_handle, db_name, client_addr)
    values(\'%s\',\'%s\',\'%s\',\'%s\',\'false\',\'%s\',\'false\',\'%s\',\'%s\')
    on conflict(err_date,hostname,err_log)
    do update set err_count = \'%s\'
    ''' % (err_date, hostname, result, err_log, in_time, db_name, client_addr, result)
    cursor_insert_err_send_sql = get_cursor(connect)
    try:
        execute_pgerr_send = cursor_insert_err_send_sql.execute(insert_err_send_sql)
        connect.commit()
    finally:
        cursor_close(cursor_insert_err_send_sql)

# 判断，是否需要发送邮件，需要发送return true
def is_need_send(err_date,hostname,err_log):
    logger = logging.getLogger('[Parse-pglog]')
    connect_sent = get_dbops_conn()
    cur_date = time.strftime('%Y-%m-%d',time.localtime(time.time()))
    is_send_sql = ''' select is_sent from t_db_err_send 
    where to_char(err_date,\'yyyy-mm-dd\') = \'%s\'
      and hostname = \'%s\'
      and err_log = \'%s\'
    ''' % (cur_date,hostname,err_log)
    cursor_is_send_sql = get_cursor(connect_sent)
    try:
        execute_send = cursor_is_send_sql.execute(is_send_sql)
        result = cursor_is_send_sql.fetchone()
    except Exception,e:
        result = ['f']
        logger.error(e)
    finally:
        return result
        close(cursor_is_send_sql,connect_sent)

# if is_need_send = 'true':
#     send_err_mail_to_user
def send_err_mail_to_ops(dbops, connect, err_date, hostname, err_log, db_name, client_addr):
    subject = "[PGLOG ERROR]The pglog error has been reported more than 20 times in %s." % hostname
    email_msg = """
    Hi dbops,
    
        Please check this error. The error has been reported more than 20 times.
    
    DATE: %s
    HOST: %s
    DBNAME: %s
    CLIENT: %s
    ERROR: 
            %s
    
    """ % (err_date, hostname, db_name, client_addr, err_log)
    send_mail(dbops, 'pg_log_err <root@test.com>', subject, email_msg, [])
    send_mail_sql = '''update t_db_err_send set is_sent = \'true\',sent_times = now() where hostname = \'%s\' and err_log = \'%s\' and err_date = \'%s\'
    ''' % (hostname, err_log, err_date)
    cursor_send_mail_sql = get_cursor(connect)
    try:
        execute_err_to_ops = cursor_send_mail_sql.execute(send_mail_sql)
        connect.commit()
    finally:
        cursor_close(cursor_send_mail_sql)

# insert pg error log to db

def insert_pgerr_to_db(conn_insert,hostname,err_msg):
    #cur_date = time.strftime('%Y-%m-%d',time.localtime(time.time()))
    logger = logging.getLogger('[Parse-pglog]')
    hostname = hostname
    try:
        err_time = err_msg[0]
        db_user = err_msg[4]
        db_name = err_msg[5]
        client_addr = err_msg[6]
        err_log_level = err_msg[7]
        err_log = err_msg[8]
        err_date = err_time[:10]
        if '\'' in err_log:
            err_log = err_log.replace('\'','\"')
        sql_insert_err = '''insert into t_db_err_log(err_date, hostname, err_time, db_user, db_name, client_addr, log_level, err_log) 
        values (\'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\', \'%s\')
        ''' % (err_date, hostname, err_time, db_user, db_name, client_addr, err_log_level, err_log)
        cursor_in_err = get_cursor(conn_insert)
        execute_insert = cursor_in_err.execute(sql_insert_err)
        logger.info('Execute %s ' % sql_insert_err)
        conn_insert.commit()
        logger.info('Commited!')
        cursor_close(cursor_in_err)
    except Exception,e:
        logger.error(e)


# compute err times
def check_is_send(hostname, err_msg):
    logger = logging.getLogger('[Parse-pglog]')
    connect = get_dbops_conn()
    err_date = err_msg[0][:10]
    db_name = err_msg[5]
    client_addr = err_msg[6]
    err_log = err_msg[8]
    logger.info('check_is_send: err_date: %s , hostname %s , err_log: %s'% (err_date , hostname, err_log))
    com_res = comput_pgerr_times(connect,err_date,hostname,err_log)
    if com_res:
        res = com_res[0]
        if res > 20:
            upsert_pgerr_send(connect, err_date, hostname, err_log, res, db_name, client_addr)
            is_send = is_need_send(err_date,hostname,err_log)[0]
            #res_is_send = is_send[0]
            logger.info('check_is_send :  is_send: %s' % (is_send))
            if not is_send:
                logger.info('Need send mail! send_err_mail_to_ops(%s,%s,%s,%s,%s,%s,%s)' % (dbops, connect, err_date, hostname, err_log, db_name,client_addr))
                send_err_mail_to_ops(dbops, connect, err_date, hostname, err_log, db_name, client_addr)
    conn_close(connect)


def main():
    # Usage()
    logfile = '/home/site/parse_pglog/log_parse_pglog.log'
    logger = logging.getLogger('[Parse-pglog]')
    logger.setLevel(logging.INFO)  
    handler = logging.FileHandler(logfile, mode='a')
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.info('Start to parse pglog')

    p = multiprocessing.Pool(8)
    logger.info('Open multiprocessing pool 8.')
    
    while True:
        datas_v = get_data_kafka()
        logger.info('Connect kafka.')
        conn_insert = get_dbops_conn()
        logger.info('Connect DB.')
        # fo = open_file_for_a('kafka_data.txt')
        for data_v in datas_v:
            err_j_data = find_err_message(data_v) # contains error message
            if err_j_data is not None:
                hostname = get_host(err_j_data)
                match_err_msg = match_msg(err_j_data) # message to list
                insert_pgerr_to_db(conn_insert,hostname,match_err_msg)
                try:
                    logger.info('err_time:%s , hostname:%s , err_msg: %s' % (match_err_msg[0][:10], hostname, match_err_msg[8]))
                except Exception,e:
                    logger.info(e)
                # insert_err_to_file(fo,hostname,match_err_msg)
                p.apply_async(check_is_send, args=(hostname,match_err_msg,))
        print "for end!"
        p.close()
        p.join()
    print "while end!"
    conn_close(conn_insert)
        #fo.close()


if __name__ == "__main__":
    main()

