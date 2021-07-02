import boto3
import requests
import time
import psycopg2
import datetime
import subprocess
import sys
import paramiko
from paramiko import SSHClient, AutoAddPolicy
import os
from LogHandler import LogHandler
from datetime import datetime


dateFormat = datetime.today().strftime('%Y%m%d')
config      = {
        'log_level':    'INFO',
        'log_file':     os.getcwd()+'/log/healthcheck_' + dateFormat + '.log',
}

dicProperties = {}

def init_global():
        global logger
        logger = (LogHandler(level=config['log_level'].upper(), logfile=config['log_file'], script_invocation=sys.argv)).getLogger()


def add_this_arg(func):
    def wrapped(*args, **kwargs):
        return func(wrapped, *args, **kwargs)
    return wrapped

@add_this_arg
def conn(this):
    try:
        logger.info("Connecting to DB...")
        this.connection  = psycopg2.connect(
            database="postgres",
            user="postgres",
            password="London123",
            host="demodb.cyszvz89y4ek.ap-south-1.rds.amazonaws.com",
            port='5432'
            )
        logger.info("Connected to DB")
        this.cur = this.connection.cursor()
        this.cur.execute('SELECT version()')
        db_version = this.cur.fetchone()
    except OperationalError as err:
        logger.error("Connection Error, Please check the connetion parameters") 

def get_instances():
    instance=[]
    logger.info("Getting EC2 instances...")
    client = boto3.client('ec2')
    Myec2=client.describe_instances(Filters=[{'Name': 'vpc-id','Values': ['vpc-028e9841f1d8e34f6']}])
    for pythonins in Myec2['Reservations']:
        for printout in pythonins['Instances']:
            for printname in printout['Tags']:
            
                try:
                    public_IP= printout['PublicIpAddress']
            
                except:    
                    instance=[[printout['InstanceId'],printout['InstanceType'],printout['State']['Name'],printname['Value'],printout['PrivateIpAddress']]] +instance
    return instance


def basic_HealthChecks(instance):
    #healthstatus[name_of_instance,private_ip,active(1)/inactive(0),okayi(1)/notokay(0)]
    healthstatus=[]
    for ec2_inc in instance:
        name_of_instance = ec2_inc[3]
        private_ip = ec2_inc[4]
        status = ec2_inc[2]
        if name_of_instance.find('passive') != -1:
            if status == "stopped":
                healthstatus=[name_of_instance,private_ip,0,1] + healthstatus
            else:
                 healthstatus=[name_of_instance,private_ip,0,0] + healthstatus

        else:
            if status == "running":
                healthstatus=[name_of_instance,private_ip,1,1] + healthstatus
                ssh(private_ip)
            else:
                 healthstatus=[name_of_instance,private_ip,1,0] + healthstatus
    return healthstatus
            
def check_GW_Status(healthstatus):
    try:
        conn()
        logger.info("Connecting to Load Blancer...")
        r = requests.head("http://DemoLBNew-743292191.ap-south-1.elb.amazonaws.com")
        
        ts = datetime.now()
        postgres_insert_query = """ INSERT INTO public."WS_connection_check" (timestamp,stautus) VALUES (%s,%s)"""
        record_to_insert = (ts, r.status_code)
        
        try:
            logger.info("Inserting record to public.WS_connection_check")
            conn.cur.execute(postgres_insert_query, record_to_insert)
            conn.connection.commit()
            count = conn.cur.rowcount
            logger.info(str(count)+ ", Record inserted successfully into public.WS_connection_check table")
        except:
            logger.error("Invalid sql instert please check")
    except requests.ConnectionError:
        logger.error("failed to connect")

def ssh(ip):
    client = SSHClient()
    client.load_system_host_keys()
    client.load_host_keys('/home/ec2-user/.ssh/known_hosts')
    client.set_missing_host_key_policy(AutoAddPolicy())

    privatekeyfile = os.path.expanduser('/home/ec2-user/.ssh/server11.pem')
    mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)

    #client.connect('ip-10-0-30-130.ap-south-1.compute.internal', username='ec2-user', key_filename='/home/ec2-user/.ssh/server11.pem', passphrase='')
    try:
        logger.info("Connecting to " + ip)
        client.connect(ip, username='ec2-user', pkey = mykey)
    except:
        logger.error("Failed to connect to " + ip)

    logger.info("Checking WS of " + ip)
    stdin, stdout, stderr = client.exec_command('curl -i http://localhost') 
    a=str(stdout.read())
    
    if len(a) == 3:
        logger.error("WS not running, starting httpd on " + ip)
        stdin, stdout, stderr = client.exec_command('sudo apachectl start')
        time.sleep(5)
        stdin, stdout, stderr = client.exec_command('curl -i http://localhost')
        a=str(stdout.read())
        if len(a) == 3:
            logger.error("Failed to start httpd on " + ip)
        else:
            logger.info("Started httpd on " + ip)
    else:
        logger.info("WS is runningi on " + ip)

    logger.info("Closing the connection to " + ip)
    client.close()

def main():
    init_global()    
    check_GW_Status(basic_HealthChecks(get_instances()))

if __name__ == '__main__':
    main()
