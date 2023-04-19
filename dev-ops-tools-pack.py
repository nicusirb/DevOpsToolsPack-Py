import botocore
import boto3
import json
import os
import logging
from datetime import date, datetime
import paramiko
import time

from utils.functions_vpc import *
from utils.functions_ec2 import *

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


def main(project='dev-ops-tools-pack'):
    """
    Start boto3 session, get config from ~/.aws/config , ~/.aws/credentials:
    """
    # Init connections
    tic = time.perf_counter()
    logger.info("Initiate AWS connections from EC2 installation.")
    session = boto3.Session()
    client = boto3.client('ec2')
    ec2 = boto3.resource('ec2', region_name=session.region_name)

    # Create VPC
    vpc = create_vpc(name = project, cidr_block = "10.0.0.0/26")
    logger.info(f"VPC created. Associated ID '{vpc['Vpc']['VpcId']}'")
    vpce = create_vpc_endpoint(name = project+"-s3", vpc_id = vpc['Vpc']['VpcId'] ,service_name = "com.amazonaws." + session.region_name + ".s3")
    logger.info(f"VPC Endpoint created. Associated ID '{vpce['VpcEndpoint']['VpcEndpointId']}'")
    
    # Create Internet Gateway
    internet_gateway = create_internet_gateway(name = project + "-igw")
    logger.info(f"Internet Gateway created. Associated ID '{internet_gateway['InternetGateway']['InternetGatewayId']}'")
    ec2.InternetGateway(internet_gateway['InternetGateway']['InternetGatewayId']).attach_to_vpc(VpcId = vpc['Vpc']['VpcId'])

    # Create 4 subnets in first 2 availability zones
    availability_zones = client.describe_availability_zones()['AvailabilityZones'][0:2]
    
    private_subnet1 = create_subnet(name = project + "-subnet-private1-" + availability_zones[0]['ZoneName'],
                                    vpc_id = vpc['Vpc']['VpcId'],
                                    availability_zone = availability_zones[0]['ZoneName'], 
                                    cidr_block = "10.0.0.32/28")
    # logger.info(f"Private Subnet 1 created with: \n{json.dumps(private_subnet1, indent=4, default=json_datetime_serializer)}")
    logger.info(f"Private Subnet 1 created. AvailabilityZone: '{private_subnet1['Subnet']['AvailabilityZone']}' ; CidrBlock: '{private_subnet1['Subnet']['CidrBlock']}'. Associated ID '{private_subnet1['Subnet']['SubnetId']}'")
   
    private_subnet2 = create_subnet(name = project + "-subnet-private2-" + availability_zones[1]['ZoneName'],
                                    vpc_id = vpc['Vpc']['VpcId'],
                                    availability_zone = availability_zones[1]['ZoneName'],  
                                    cidr_block = "10.0.0.48/28")
    logger.info(f"Private Subnet 2 created. AvailabilityZone: '{private_subnet2['Subnet']['AvailabilityZone']}' ; CidrBlock: '{private_subnet2['Subnet']['CidrBlock']}'. Associated ID '{private_subnet2['Subnet']['SubnetId']}'")
   
    public_subnet1 = create_subnet(name = project + "-subnet-public1-" + availability_zones[0]['ZoneName'],
                                   vpc_id = vpc['Vpc']['VpcId'],
                                   availability_zone = availability_zones[0]['ZoneName'], 
                                   cidr_block = "10.0.0.0/28")
    logger.info(f"Public Subnet 1 created. AvailabilityZone: '{public_subnet1['Subnet']['AvailabilityZone']}' ; CidrBlock: '{public_subnet1['Subnet']['CidrBlock']}'. Associated ID '{public_subnet1['Subnet']['SubnetId']}'")
   
    public_subnet2 = create_subnet(name = project + "-subnet-public2-" + availability_zones[1]['ZoneName'],
                                   vpc_id = vpc['Vpc']['VpcId'],
                                   availability_zone = availability_zones[1]['ZoneName'], 
                                   cidr_block = "10.0.0.16/28")
    logger.info(f"Public Subnet 1 created. AvailabilityZone: '{public_subnet2['Subnet']['AvailabilityZone']}' ; CidrBlock: '{public_subnet2['Subnet']['CidrBlock']}'. Associated ID '{public_subnet2['Subnet']['SubnetId']}'")



    # create NAT gateway in public subnet2
    public_subnet1_eip = client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip','Tags': [{'Key': 'Name','Value': project + "-subnet-public1-eip" }]}])
    public_subnet2_eip = client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip','Tags': [{'Key': 'Name','Value': project + "-subnet-public2-eip" }]}])
    public_subnet1_ng = client.create_nat_gateway(SubnetId=public_subnet1['Subnet']['SubnetId'], AllocationId=public_subnet1_eip['AllocationId'], 
                                                  TagSpecifications=[{'ResourceType': 'natgateway','Tags': [{'Key': 'Name','Value': project + "-subnet-public1-ng" }]}])
    logger.info(f"Created NAT Gateway for Public Subnet 1 with Elastic IP '{public_subnet1_eip['PublicIp']}'. Associated ID '{public_subnet1_ng['NatGateway']['NatGatewayId']}'")
    public_subnet2_ng = client.create_nat_gateway(SubnetId=public_subnet2['Subnet']['SubnetId'], AllocationId=public_subnet2_eip['AllocationId'], 
                                                  TagSpecifications=[{'ResourceType': 'natgateway','Tags': [{'Key': 'Name','Value': project + "-subnet-public2-ng" }]}])
    logger.info(f"Created NAT Gateway for Public Subnet 2 with Elastic IP '{public_subnet2_eip['PublicIp']}'. Associated ID '{public_subnet2_ng['NatGateway']['NatGatewayId']}'")
    logger.info(f"Waiting for gateways to be available...")
    waiter = client.get_waiter('nat_gateway_available')
    waiter.wait(NatGatewayIds=[public_subnet1_ng['NatGateway']['NatGatewayId'],public_subnet2_ng['NatGateway']['NatGatewayId']])

    toc = time.perf_counter()
    print(f"Time took -> {toc - tic:0.4f} seconds")

    # Create Public Route Table
    rtb_public = create_route_table(name = project + "-rtb-public", vpc_id = vpc['Vpc']['VpcId'])
    logger.info(f"Public Route Table created. Associated ID '{rtb_public['RouteTable']['RouteTableId']}'")
    
    # Associate Public Subnets to Public Route Table
    create_route(route_table=rtb_public['RouteTable']['RouteTableId'], destination="0.0.0.0/0", target=internet_gateway['InternetGateway']['InternetGatewayId'], target_type="InternetGateway")

    ec2.RouteTable(rtb_public['RouteTable']['RouteTableId']).associate_with_subnet(SubnetId = public_subnet1['Subnet']['SubnetId'])
    ec2.RouteTable(rtb_public['RouteTable']['RouteTableId']).associate_with_subnet(SubnetId = public_subnet2['Subnet']['SubnetId'])

    # Create Private Route Table 1
    rtb_private1 = create_route_table(name = project + "-rtb-private1-" + availability_zones[0]['ZoneName'], vpc_id = vpc['Vpc']['VpcId'])
    logger.info(f"Private Route Table 1 created. Associated ID '{rtb_private1['RouteTable']['RouteTableId']}'")
    # Create route to NAT Gateway
    create_route(route_table=rtb_private1['RouteTable']['RouteTableId'], destination="0.0.0.0/0", target=public_subnet1_ng['NatGateway']['NatGatewayId'], target_type="NatGateway")
    # Link Route Table to Subnet
    ec2.RouteTable(rtb_private1['RouteTable']['RouteTableId']).associate_with_subnet(SubnetId = private_subnet1['Subnet']['SubnetId'])
    

    # Create Private Route Table 2
    rtb_private2 = create_route_table(name = project + "-rtb-private2-" + availability_zones[1]['ZoneName'], vpc_id = vpc['Vpc']['VpcId'])
    logger.info(f"Private Route Table 2 created. Associated ID '{rtb_private2['RouteTable']['RouteTableId']}'")
    # Create route to NAT Gateway
    create_route(route_table=rtb_private2['RouteTable']['RouteTableId'], destination="0.0.0.0/0", target=public_subnet2_ng['NatGateway']['NatGatewayId'], target_type="NatGateway")
    # Link Route Table to Subnet
    ec2.RouteTable(rtb_private2['RouteTable']['RouteTableId']).associate_with_subnet(SubnetId = private_subnet2['Subnet']['SubnetId'])
    

    client.modify_vpc_endpoint(VpcEndpointId=vpce['VpcEndpoint']['VpcEndpointId'], 
                               AddRouteTableIds=[rtb_private1['RouteTable']['RouteTableId'], rtb_private2['RouteTable']['RouteTableId']])
    logger.info(f"Added Private Route Tables to VPC Endpoint.")
    toc = time.perf_counter()
    print(f"Time took -> {toc - tic:0.4f} seconds")
    ##
    ## DONE VPC -> ID: vpc['Vpc']['VpcId']
    ##


    ## 
    ## Start EC2
    ##

    ## Reduce variables...
    vpc_id = vpc['Vpc']['VpcId']
    private_subnet1_id = private_subnet1['Subnet']['SubnetId']
    private_subnet2_id = private_subnet2['Subnet']['SubnetId']
    public_subnet1_id = public_subnet1['Subnet']['SubnetId']
    public_subnet2_id = public_subnet2['Subnet']['SubnetId']

    
    create_security_group(group_name=project+"-sgr", subnet_id=private_subnet1_id, ip_permissions="0.0.0.0/0:22,0.0.0.0/0:80,0.0.0.0/0:443")
    
    # Set EC2 properties
    image_id, instance_type, key_pair_name_, instance_size = get_ec2_custom_template("free-ec2-instance")
    # print(f"Image ID: {image_id}\nInstance type: {instance_type}\nKey pair name: {key_pair_name}")
    key_pair_name = key_pair_name_ + "-" + str(time.perf_counter()).split('.')[1]
    create_ec2_key_pair(key_name=key_pair_name)

    private_subnet1_sgr = create_security_group(group_name = project+"-sgr", 
                                                ip_permissions = "0.0.0.0/0:22,0.0.0.0/0:80,0.0.0.0/0:443", 
                                                subnet_id  = private_subnet1_id )
    # Create EC2 instances
    ec2_jenkins = create_ec2_instance(session.region_name, image_id, instance_type, key_pair_name, instance_size, private_subnet1_id, private_subnet1_sgr, instance_name="dot_jenkins")
    # ec2_gitea = create_ec2_instance(session.region_name, image_id, instance_type, key_pair_name, instance_size, private_subnet1_id,instance_name="dot_gitea")
    # ec2_artifactory = create_ec2_instance(session.region_name, image_id, instance_type, key_pair_name, instance_size, private_subnet1_id, instance_name="dot_artifactory")

    ec2_nginx = create_ec2_instance(session.region_name, image_id, instance_type, key_pair_name, instance_size, public_subnet1_id, private_subnet1_sgr, instance_name="dot_nginx")

    logger.info("Jenkins EC2 -|> ")
    logger.info(ec2_jenkins)

    logger.info(f"Listing EC2 instances in vpc '{vpc_id}':")
    for instance in client.describe_instances(Filters=[{'Name': 'vpc-id', 'Values':[vpc_id]}])['Reservations']:
        for tag in instance['Instances'][0]['Tags']:
                if tag['Key'] == 'Name':
                        logger.info(f"  - Instance Name: {tag['Value']}, ID: {instance['Instances'][0]['InstanceId']}, State: {instance['Instances'][0]['State']['Name']}, Type: {instance['Instances'][0]['InstanceType']}")

    toc = time.perf_counter()
    print(f"Time took -> {toc - tic:0.4f} seconds")

    ## Connect SSH to a temporary Elastic IP Allocated to EC2 NGinx 
    ec2_ssh_key = paramiko.RSAKey.from_private_key_file(os.path.expanduser('~') + "/shadow/" +key_pair_name + ".pem")
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        temp_elastic_ip = client.allocate_address(Domain='vpc', TagSpecifications=[{'ResourceType': 'elastic-ip','Tags': [{'Key': 'Name','Value': project + "-temp-eip" }]}])
        client.associate_address(AllocationId=temp_elastic_ip['AllocationId'], InstanceId=ec2_nginx.id)
    except botocore.exceptions.ClientError as e:
        logger.error(e)

    try:
        # Connect ssh to EC2 instance using temporary elastic IP
        ssh_client.connect(hostname=temp_elastic_ip['PublicIp'], username="ubuntu", pkey=ec2_ssh_key)

        # Copy Install Scripts
        sftp = ssh_client.open_sftp()

        # Create subdir
        sftp.mkdir("./resources")
        for root, dirs, files in os.walk("./resources", topdown=True):
            for name in dirs:
                sftp.mkdir(os.path.join(root, name))
            for name in files:
                sftp.put(os.path.join(root, name),os.path.join(root, name))
        

        logger.info("Copy ssh-key to EC2 instance.")
        ## Copy ssh-key for further ssh-ing :)
        sftp.mkdir("./shadow")
        sftp.put("./shadow/" +key_pair_name + ".pem", "./shadow/" +key_pair_name + ".pem")
        sftp.close()
        ssh_client.exec_command("chmod 400 ./shadow/" +key_pair_name + ".pem")

        logger.info("Copy resources to all EC2 instances...")
        ## Copy resources to other EC2 instances
        stdin, stdout, stderr = ssh_client.exec_command("scp -r -i ./shadow/" +key_pair_name + ".pem ./resources/ ubuntu@" + ec2_jenkins.private_ip + ":~")
        # stdin, stdout, stderr = ssh_client.exec_command("scp -r -i ./shadow/" +key_pair_name + ".pem ./resources/ ubuntu@" + ec2_gitea.private_ip + ":~")
        # stdin, stdout, stderr = ssh_client.exec_command("scp -r -i ./shadow/" +key_pair_name + ".pem ./resources/ ubuntu@" + ec2_artifactory.private_ip + ":~")

        logger.info("Installing docker...")
        stdin, stdout, stderr = ssh_client.exec_command("sudo /bin/bash ./resources/ubuntu/docker_install.sh")
        stdin, stdout, stderr = ssh_client.exec_command("ssh -i ./shadow/" +key_pair_name + ".pem ubuntu@"+ ec2_jenkins.private_ip +" sudo /bin/bash ./resources/ubuntu/docker_install.sh")
        # stdin, stdout, stderr = ssh_client.exec_command("ssh -i ./shadow/" +key_pair_name + ".pem ubuntu@"+ ec2_gitea.private_ip +" sudo /bin/bash ./resources/ubuntu/docker_install.sh")
        # stdin, stdout, stderr = ssh_client.exec_command("ssh -i ./shadow/" +key_pair_name + ".pem ubuntu@"+ ec2_artifactory.private_ip +" sudo /bin/bash ./resources/ubuntu/docker_install.sh")


        logger.info("Installing NGinx")
        stdin, stdout, stderr = ssh_client.exec_command("sudo /bin/bash ./resources/nginx/install.sh")
        logger.info("Installing Jenkins")
        stdin, stdout, stderr = ssh_client.exec_command("ssh -i ./shadow/" +key_pair_name + ".pem ubuntu@"+ ec2_jenkins.private_ip +" sudo /bin/bash ./resources/jenkins/install.sh")
        logger.info("Installing Gitea")
        # stdin, stdout, stderr = ssh_client.exec_command("ssh -i ./shadow/" +key_pair_name + ".pem ubuntu@"+ ec2_gitea.private_ip +" docker-compose -f ./resources/gitea/docker-compose.yaml up -d")
        logger.info("Installing Artifactory")
        # stdin, stdout, stderr = ssh_client.exec_command("ssh -i ./shadow/" +key_pair_name + ".pem ubuntu@"+ ec2_artifactory.private_ip +"docker-compose -f ./resources/artifactory/docker-compose.yaml up -d")

        # close the client connection once the job is done
        # Also needed to allow user to run 'docker' commands
        ssh_client.close()

        toc = time.perf_counter()
        print(f"Time took -> {toc - tic:0.4f} seconds")

    except Exception as e:
        logger.error(e)

if __name__ == '__main__':
    main()
