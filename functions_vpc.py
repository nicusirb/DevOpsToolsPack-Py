import logging
from datetime import date, datetime
import botocore
import boto3

# logger config
logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

def json_datetime_serializer(obj):
    """
    Helper method to serialize datetime fields
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

def create_vpc(name, cidr_block):
    """
    CidrBlock='10.0.0.0/26'
    """
    client = boto3.client('ec2')
    try:
        vpc = client.create_vpc(
            CidrBlock=cidr_block,
            AmazonProvidedIpv6CidrBlock=False,
            InstanceTenancy='default',
            TagSpecifications=[
                {
                    'ResourceType': 'vpc',
                    'Tags': [
                        {
                            'Key': 'Project',
                            'Value': 'DevOps Tools Pack'
                        },
                        {
                            'Key': 'Name',
                            'Value': name
                        },
                    ]
                },
            ]
        )
        
        
        # wait for the VPC to become available
        waiter = client.get_waiter('vpc_available')
        waiter.wait(VpcIds=[vpc['Vpc']['VpcId']])

        # enable DNS support in the VPC
        client.modify_vpc_attribute(VpcId=vpc['Vpc']['VpcId'], EnableDnsSupport={'Value': True})
        client.modify_vpc_attribute(VpcId=vpc['Vpc']['VpcId'], EnableDnsHostnames={'Value': True})
        return vpc
    except botocore.exceptions.ClientError as error: 
        if error.response['Error']['Code'] == 'VpcLimitExceeded':
            logger.exception(f"The maximum number of VPCs has been reached.")
            raise
        else:
            logger.exception("Unexpected error: ", error)
            raise

def create_subnet(name, vpc_id, availability_zone, cidr_block):
    """
    AvailabilityZone='eu-central-1a',
    AvailabilityZoneId='euc1-az2',
    CidrBlock='10.0.0.0/28',
    """
    client = boto3.client('ec2')
    response = client.create_subnet(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'subnet',
                'Tags': [
                    {
                        'Key': 'Project',
                        'Value': 'DevOps Tools Pack'
                    },
                    {
                        'Key': 'Name',
                        'Value': name
                    },
                ]
            },
        ],
        AvailabilityZone=availability_zone,
        CidrBlock=cidr_block,
        Ipv6Native=False
    )
    return response
 
def create_internet_gateway(name):
    client = boto3.client('ec2')
    try:
        response = client.create_internet_gateway(
            TagSpecifications=[
                {
                    'ResourceType': 'internet-gateway',
                    'Tags': [
                        {
                            'Key': 'Project',
                            'Value': 'DevOps Tools Pack'
                        },
                        {
                            'Key': 'Name',
                            'Value': name
                        },
                    ]
                },
            ],
        )
        return response
    except botocore.exceptions.ClientError as error: 
        if error.response['Error']['Code'] == 'InternetGatewayLimitExceeded':
            logger.exception(f"[Error] The maximum number of internet gateways has been reached.")
            raise
        else:
            logger.exception("Unexpected error: ", error)
            raise
  
def create_route_table(name, vpc_id):
    client = boto3.client('ec2')
    response = client.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'route-table',
                'Tags': [
                    {
                        'Key': 'Project',
                        'Value': 'DevOps Tools Pack'
                    },
                    {
                        'Key': 'Name',
                        'Value': name
                    },
                ]
            },
        ]
    )
    return response

def create_route(route_table, destination, target, target_type):
    client = boto3.client('ec2')
    response = None
    match target_type:
        case "VPCEndpoint":
                response = client.create_route(
                    RouteTableId=route_table,
                    DestinationPrefixListId=destination,
                    VpcEndpointId=target
                )
                logger.info(f"Create route - Destination: '{destination}' - Target: VPCEndpoint '{target}'")
        case "InternetGateway":
                response = client.create_route(
                    RouteTableId=route_table,
                    DestinationCidrBlock=destination,
                    GatewayId=target
                )
                logger.info(f"Create route - Destination: '{destination}' - Target: InternetGateway '{target}'")
        case "NatGateway":
                response = client.create_route(
                    RouteTableId=route_table,
                    DestinationCidrBlock=destination,
                    NatGatewayId=target
                )
                logger.info(f"Create route - Destination: '{destination}' - Target: NatGateway '{target}'")
    return response

def create_vpc_endpoint(name, vpc_id, service_name, route_tables=[], subnets=[], security_groups=[]):
    """
    VpcId='vpc-0111ac0194d93a36b',
    ServiceName='com.amazonaws.eu-central-1.s3',
    !! Parameters: route_tables, subnets, security_groups - are type list
    """
    client = boto3.client('ec2')
    response = client.create_vpc_endpoint(
        VpcEndpointType='Gateway',
        VpcId=vpc_id,
        ServiceName=service_name,
        RouteTableIds=route_tables,
        SubnetIds=subnets,
        SecurityGroupIds=security_groups,
        TagSpecifications=[
            {
                'ResourceType': 'vpc-endpoint',
                'Tags': [
                    {
                        'Key': 'Project',
                        'Value': 'DevOps Tools Pack'
                    },
                    {
                        'Key': 'Name',
                        'Value': name
                    },
                ]
            },
        ]
    )
    return response


def get_new_vpc(project = "devops-tools-pack"):
    # Init connections
    logger.info("Initiate AWS connections from VPC creation.")
    session = boto3.Session()
    client = boto3.client('ec2')
    ec2 = boto3.resource('ec2')
    
    # Create VPC
    vpc = create_vpc(name = project, cidr_block = "10.0.0.0/26")
    logger.info(f"VPC created. Associated ID '{vpc['Vpc']['VpcId']}'")
    vpce = create_vpc_endpoint(name = "devops-tools-pack-vpce-s3", vpc_id = vpc['Vpc']['VpcId'] ,service_name = "com.amazonaws." + session.region_name + ".s3")
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

    return vpc['Vpc']['VpcId']

if __name__ == '__main__':
    get_new_vpc()