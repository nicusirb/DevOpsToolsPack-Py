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

def get_new_vpc():
    logger.error("Please refer to main app, VPC main function isn't callable.")

if __name__ == '__main__':
    get_new_vpc()