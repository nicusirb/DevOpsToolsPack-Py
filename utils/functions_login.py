import botocore
import boto3
import json
import os
import logging
from datetime import date, datetime
from flask_socketio import SocketIO, emit

# logger config
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

def login(aws_access_key_id, aws_secret_access_key, region):

    if not os.path.exists(os.path.expanduser("~") + "/.aws"):
        os.makedirs(os.path.expanduser("~") + "/.aws") 

    with open(os.path.expanduser("~") + "/.aws/config", "w+") as file:
        file.write(f"[default] \n")
        file.write(f"region = {region} \n")
        file.write(f"output = json \n")

    with open(os.path.expanduser("~") + "/.aws/credentials", "w+") as file:
        file.write(f"[default] \n")
        file.write(f"aws_access_key_id = {aws_access_key_id} \n")
        file.write(f"aws_secret_access_key = {aws_secret_access_key} \n")
    
    try:
        client = boto3.client('ec2')
        client.describe_instances()
        emit('output', 'Login success!')
    except:
        emit('output', 'Something went wrong with login. Please check credentials!')
        raise

def main():
    logger.warning("Not from here! 🎄")

if __name__ == '__main__':
    main()