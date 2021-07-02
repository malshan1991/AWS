import boto3
import requests
import time
import datetime
import subprocess
import paramiko
from paramiko import SSHClient, AutoAddPolicy
from LogHandler import LogHandler
from scp import SCPClient
import sys
import os, getopt
from datetime import datetime


dateFormat = datetime.today().strftime('%Y%m%d')
config      = {
        'log_level':    'INFO',
        'log_file':     os.getcwd()+'/log/houskeep_' + dateFormat + '.log',
}

dicProperties = {}

def init_global():
        global logger
        logger = (LogHandler(level=config['log_level'].upper(), logfile=config['log_file'], script_invocation=sys.argv)).getLogger()


def add_this_arg(func):
    def wrapped(*args, **kwargs):
        return func(wrapped, *args, **kwargs)
    return wrapped


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

    scp = SCPClient(client.get_transport())

    scp.get('/var/log/httpd/access_log','./download/')
    os.system('tar -cvf ./tardir/' + ip + '_' + dateFormat + '.tar ./download/')    
    os.system('rm -rf ./download/*')
    upload_to_aws('./tardir/' + ip + '_' + dateFormat + '.tar','demobucketmalshan','logarchive/{}'.format(ip + '_' + dateFormat + '.tar'))
    client.close()

def upload_to_aws(local_file, bucket, s3_file):
    s3 = boto3.client('s3')

    try:
        s3.upload_file(local_file, bucket, s3_file)
        logger.info(local_file + " Uploaded Successfully to"  + bucket)
        return True
    except FileNotFoundError:
        logger.error("The file was not found " + local_file)
        return False
    except NoCredentialsError:
        logger.error("Credentials not available")
        return False

def main():
    init_global()    
    basic_HealthChecks(get_instances())

if __name__ == '__main__':
    main()
