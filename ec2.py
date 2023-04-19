import botocore
import boto3
import json
import os
import logging
from datetime import date, datetime
import paramiko

from functions_vpc import *

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
        logger.info(f"EC2 instance '{instance_name}' '{instance.id}' created in region '{region_name}' with type '{instance_type}' and key '{key_pair_name}'.")
    else:
        logger.info(f"EC2 instance '{instance.id}' created in region '{region_name}' with type '{instance_type}' and key '{key_pair_name}'.")
    logger.info("Waiting for instance to start...")
    instance.wait_until_running()
    instance.reload() # Reload to get public IP
    if instance.public_ip_address == None:
        logger.info(f"EC2 instance is running! No Public IP Available ; Private IP: '{instance.private_ip_address}'.")
    else:
        logger.info(f"EC2 instance is running! Public IP: '{instance.public_ip_address}' ; Private IP: '{instance.private_ip_address}'.")

    return instance

def create_ec2_key_pair(region_name, key_name):
    ## Allow call with no key, do nothing
    if key_name == None:
        return
    ## Check if key exists
    client = boto3.client('ec2')
    try:
        json_data = json.loads(json.dumps(client.describe_key_pairs(KeyNames=[key_name]), indent=2, default=str))
        logger.warning(f"Key <{json_data['KeyPairs'][0]['KeyName']}> exists, created at: <{json_data['KeyPairs'][0]['CreateTime']}>")
    except botocore.exceptions.ClientError as error: 
        if error.response['Error']['Code'] == 'NotFound':
            logger.info("Key does not exists. Creating...")
            ec2 = boto3.resource('ec2', region_name=region_name)
            pem_key = ec2.create_key_pair(KeyName=key_name)
            f = open("~/pem_keys/"+key_name+".pem", "a")
            f.write(pem_key['KeyMaterial'])
            f.close()
        else:
            logger.error(f"Unexpected error: {error}")
    if os.path.isfile(f"~/pem_keys/{key_name}.pem"):
        logger.info(f"Key {key_name} was created!\n\tYou can ssh using key '~/pem_keys/{key_name}.pem'.\n\t [Notice] Please keep this key safe, this location is ephemeral.")
    else:
        logger.error(f"Could not find pem key at '~/pem_keys/{key_name}.pem'.")
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

def main(project="devops-tools-pack"):
    """
    Start boto3 session, get config from ~/.aws/config , ~/.aws/credentials:
    """
    # Init connections
    logger.info("Initiate AWS connections from EC2 installation.")
    session = boto3.Session()
    client = boto3.client('ec2')
    ec2 = boto3.resource('ec2')

    create_ec2_key_pair(region_name=session.region_name, key_name=None)
    # create_security_group(group_name=project+"-sgr", ip_permissions="0.0.0.0/0:22,0.0.0.0/0:80,0.0.0.0/0:443")
    
    # vpc = get_new_vpc(project)
    vpc = 'vpc-0064c49ba4cffbcda'
    project = 'TEST-02'
    
    logger.info(f"Searching VPC for networks...")

    # Get Subnets of VPC
    private_subnet1 = client.describe_subnets(Filters=[{'Name': 'tag:Name', 'Values': [project+'-subnet-private1-*']},
                                                        {'Name': 'vpc-id', 'Values': [vpc]}])['Subnets'][0]['SubnetId']

    private_subnet2 = client.describe_subnets(Filters=[{'Name': 'tag:Name', 'Values': [project+'-subnet-private2-*']},
                                                        {'Name': 'vpc-id', 'Values': [vpc]}])['Subnets'][0]['SubnetId']

    public_subnet1 = client.describe_subnets(Filters=[{'Name': 'tag:Name', 'Values': [project+'-subnet-public1-*']},
                                                        {'Name': 'vpc-id', 'Values': [vpc]}])['Subnets'][0]['SubnetId']

    public_subnet2 = client.describe_subnets(Filters=[{'Name': 'tag:Name', 'Values': [project+'-subnet-public2-*']},
                                                        {'Name': 'vpc-id', 'Values': [vpc]}])['Subnets'][0]['SubnetId']

    logger.info(f"Found Private Subnet 1 : '{private_subnet1}'")
    logger.info(f"Found Private Subnet 2 : '{private_subnet2}'")
    logger.info(f"Found Public Subnet 1 : '{public_subnet1}'")
    logger.info(f"Found Public Subnet 2 : '{public_subnet2}'")
    # Set EC2 properties
    image_id, instance_type, key_pair_name, instance_size = get_ec2_custom_template("free-ec2-instance")
    # print(f"Image ID: {image_id}\nInstance type: {instance_type}\nKey pair name: {key_pair_name}")


    private_subnet1_sgr = create_security_group(group_name = "devops-tools-pack-sgr", 
                                                ip_permissions = "0.0.0.0/0:22,0.0.0.0/0:80,0.0.0.0/0:443", 
                                                subnet_id  = private_subnet1 )
    # Create EC2 instances
    ec2_jenkins = create_ec2_instance(session.region_name, image_id, instance_type, key_pair_name, instance_size, private_subnet1, private_subnet1_sgr, instance_name="dot_jenkins")
    # ec2_gitea = create_ec2_instance(session.region_name, image_id, instance_type, key_pair_name, instance_size, private_subnet1,instance_name="dot_gitea")
    # ec2_artifactory = create_ec2_instance(session.region_name, image_id, instance_type, key_pair_name, instance_size, private_subnet1, instance_name="dot_artifactory")

    ec2_nginx = create_ec2_instance(session.region_name, image_id, instance_type, key_pair_name, instance_size, public_subnet1, private_subnet1_sgr, instance_name="dot_nginx")


    logger.info(f"Listing EC2 instances in vpc '{vpc}':")
    for instance in client.describe_instances(Filters=[{'Name': 'vpc-id', 'Values':[vpc]}])['Reservations']:
        for tag in instance['Instances'][0]['Tags']:
                if tag['Key'] == 'Name':
                        logger.info(f"  - Instance Name: {tag['Value']}, ID: {instance['Instances'][0]['InstanceId']}, State: {instance['Instances'][0]['State']['Name']}, Type: {instance['Instances'][0]['InstanceType']}")

    ec2_ssh_key = paramiko.RSAKey.from_private_key_file(os.path.expanduser('~') + "/pem_keys/" +key_pair_name + ".pem")
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    #i-0a28e211ad5e33a2e

    try:
        temp_elastic_ip = client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip','Tags': [{'Key': 'Name','Value': project + "-temp-eip" }]}])
        ec2.associate_address(AllocationId=temp_elastic_ip['AllocationId'], InstanceId=ec2_nginx.id)
    except botocore.exceptions.ClientError as e:
        logger.error(e)

    try:
        # Connect ssh to EC2 instance using temporary elastic IP
        ssh_client.connect(hostname=temp_elastic_ip['PublicIp'], username="ubuntu", pkey=ec2_ssh_key)

        # Copy Ubuntu Config Script
        sftp = ssh_client.open_sftp()
        sftp.put('./resources/ubuntu/install.sh', '/tmp/install.sh')
        sftp.close()

        # Execute a command(cmd) after connecting/ssh to an instance
        stdin, stdout, stderr = ssh_client.exec_command('/bin/bash /tmp/install.sh')
        logger.info(stdout.read())
        logger.stderr(stderr.read())

        # close the client connection once the job is done
        ssh_client.close()

    except Exception as e:
        logger.error(e)

if __name__ == '__main__':
    main()
