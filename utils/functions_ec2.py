import botocore
import boto3
import json
import os
import logging
from datetime import date, datetime
import time
import socket

# logger config
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

def json_datetime_serializer(obj):
    """
    Helper method to serialize datetime fields
    json.dumps(MY_AWS_BOTO3_OBJ, indent=4, default=json_datetime_serializer)
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

def create_security_group(group_name, subnet_id, ip_permissions="0.0.0.0/0:22", group_description="Autocreated by [snick] DevOps Tools Pack"):
    client = boto3.client('ec2')

    security_groups = client.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': [group_name]}])['SecurityGroups']
    if len(security_groups) == 0:
        vpc_id = client.describe_subnets(Filters=[{'Name': 'subnet-id', 'Values': [subnet_id]}])['Subnets'][0]['VpcId']
        try:
            response = client.create_security_group(GroupName=group_name,
                                                Description=group_description,
                                                VpcId=vpc_id)
            security_group_id = response['GroupId']
            logger.info(f"Security Group Created {security_group_id} in vpc {vpc_id}.")

            ec2_ip_permissions = []
            for x in ip_permissions.split(','):
                ip_ranges = []
                for y in x.split(':')[0].split(';'):
                    ip_ranges.append({'CidrIp': y})
                ec2_ip_permissions.append({'IpProtocol': 'tcp','FromPort': int(x.split(':')[1]),'ToPort': int(x.split(':')[1]),'IpRanges': ip_ranges})

            client.authorize_security_group_ingress(GroupId=security_group_id, IpPermissions=ec2_ip_permissions)
            logger.info(f"Ingress Successfully Set")
            return security_group_id
        except botocore.exceptions.ClientError as e:
            raise e
    logger.info(f"Security group '{group_name}' already exists.")
    return security_groups[0]['GroupId']

def get_ec2_instances(vpc_id):
    # ec2 = boto3.resource('ec2', region_name=region_name)
    # instances = ec2.instances.all()

    client = boto3.client('ec2')
    instances = boto3.client('ec2').describe_instances(Filters=[{'Name': 'vpc-id', 'Values':[vpc_id]}])

    return json.dumps(instances, indent=4, default=json_datetime_serializer)

def create_ec2_instance(region_name, image_id, instance_type, key_pair_name, instance_size, subnet_id, security_group, instance_name=None):
    # instance_size - Volume size in GB
    ec2 = boto3.resource('ec2', region_name=region_name)
    instance = ec2.create_instances(
        ImageId=image_id,
        InstanceType=instance_type,
        SubnetId=subnet_id,
        MinCount=1,
        MaxCount=1,
        KeyName=key_pair_name,
        SecurityGroupIds=[ security_group ],
        EbsOptimized=False,
        BlockDeviceMappings=[
            {
            'DeviceName': '/dev/xvda',
            'Ebs': {
                'Encrypted': False,
                'DeleteOnTermination': True,
                'Iops': 3000,
                'SnapshotId': 'snap-03cb54dd7b8f2094d',
                'VolumeSize': instance_size,
                'VolumeType': 'gp3',
                'Throughput': 125
            }
            }
        ],
        TagSpecifications=[
                            {
                                'ResourceType': 'instance',
                                'Tags': [
                                    {
                                        'Key': 'Name',
                                        'Value': instance_name
                                    },{
                                        'Key': 'Project',
                                        'Value': '[snick] DevOps Tools Pack'
                                    }
                                ]
                            },
                        ]
                        )[0]
    
    if instance_name != None:
        logger.info(f"EC2 instance '{instance_name}' - Region '{region_name}' - sshkey '{key_pair_name}'.")
    else:
        logger.info(f"EC2 instance - Region '{region_name}' - sshkey '{key_pair_name}'.")
    logger.info("Waiting for instance to start...")
    instance.wait_until_running()
    instance.reload() # Reload to get public IP
    if instance.public_ip_address == None:
        logger.info(f"EC2 instance is running! No Public IP Available ; Private IP: '{instance.private_ip_address}'.")
    else:
        logger.info(f"EC2 instance is running! Public IP: '{instance.public_ip_address}' ; Private IP: '{instance.private_ip_address}'.")

    return instance

def create_ec2_key_pair(key_name):
    ## Allow call with no key, do nothing
    if key_name == None:
        return
    ## Check if key exists
    client = boto3.client('ec2')
    try:
        json_data = json.loads(json.dumps(client.describe_key_pairs(KeyNames=[key_name]), indent=2, default=str))
        logger.warning(f"Key <{json_data['KeyPairs'][0]['KeyName']}> exists, created at: <{json_data['KeyPairs'][0]['CreateTime']}>")
    except botocore.exceptions.ClientError as error: 
        if error.response['Error']['Code'] == 'InvalidKeyPair.NotFound':
            logger.info("Creating ssh-key...")
            client = boto3.client('ec2')
            pem_key = client.create_key_pair(KeyName=key_name)
            with open("./shadow/"+key_name+".pem", "w") as file:
                file.write(pem_key['KeyMaterial'])
                os.system("chmod 400 ./shadow/"+key_name+".pem")
        else:
            logger.error(f"Unexpected error: {error}")
    if os.path.isfile(f"./shadow/{key_name}.pem"):
        logger.info(f"Key {key_name} was created!")
    else:
        logger.error(f"Could not find pem key at '~/shadow/{key_name}.pem'.")
        raise error
    return

def get_ec2_custom_template(x):
    """
     -- Helper Method to set specific EC2 instance templates --
    Template EC2 Instance config
    image_id, instance_type, key_pair_name, instance_size
    "ami-0fa03365cde71e0ab" - Amazon Linux 2023 AMI 2023.0.20230329.0 x86_64 HVM kernel-6.1
    "ami-0ec7f9846da6b0f61" - Canonical, Ubuntu, 22.04 LTS, amd64 jammy image build on 2023-03-25
    "t2.micro" - 1 GB RAM
    "t2.small" - 2 GB RAM
    "t2.medium" - 4 GB RAM
    "t2.large" - 8 GB RAM
    """
    
    return {
        "free-ec2-instance": ("ami-0ec7f9846da6b0f61", "t2.micro", "central-dev-key", 20),
        "small-ec2-instance": ("ami-0ec7f9846da6b0f61", "t2.small", "central-dev-key", 40),
        "medium-ec2-instance": ("ami-0ec7f9846da6b0f61", "t2.medium", "central-dev-key", 50),
        "large-ec2-instance": ("ami-0ec7f9846da6b0f61", "t2.large", "central-dev-key", 80) 
    }.get(x,"Template name not found!") 

def wait_for_port(port: int, host: str = 'localhost', timeout: float = 5.0):
    """Wait until a port starts accepting TCP connections.
    Args:
        port: Port number.
        host: Host address on which the port should exist.
        timeout: In seconds. How long to wait before raising errors.
    Raises:
        TimeoutError: The port isn't accepting connection after time specified in `timeout`.
    """
    start_time = time.perf_counter()
    while True:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                break
        except OSError as e:
            time.sleep(0.01)
            if time.perf_counter() - start_time >= timeout:
                raise TimeoutError('Waited too long for the port {} on host {} to start accepting '
                                   'connections.'.format(port, host)) from e

def main():
    logger.error("Please refer to main app, EC2 main function isn't callable.")

if __name__ == '__main__':
    main()
