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

def main():
    
    # Init connections
    logger.info("Initiate AWS connections from Remove VPC.")
    session = boto3.Session()
    client = boto3.client('ec2')
    ec2 = boto3.resource('ec2')

    vpc = 'vpc-010e63d7f59b8c2aa'
    for nat in client.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [vpc]}])['NatGateways']:
        logger.info(f"Deleting NAT Gatewaty '{nat['NatGatewayId']}'")
        client.delete_nat_gateway(NatGatewayId=nat['NatGatewayId'])

    for eip in client.describe_addresses()['Addresses']:
        logger.info(f"{eip['PublicIp']} is not associated, releasing")
        client.release_address(AllocationId=eip['AllocationId'])


    for ig in client.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id','Values': [vpc]}])['InternetGateways']:
        logger.info(f"Deleting Internet Gateway '{ig['InternetGatewayId']}'")
        client.delete_internet_gateway(InternetGatewayId=ig['InternetGatewayId'])

    for rt in client.describe_route_tables(Filters=[{'Name': 'vpc-id','Values': [vpc]}])['RouteTables']:
        logger.info(f"Deleting Route Table '{rt['RouteTableId']}'")
        client.delete_route_table(RouteTableId=rt['RouteTableId'])

    for subnet in client.describe_subnets(Filters=[{'Name': 'vpc-id','Values': [vpc]}])['Subnets']:
        logger.info(f"Deleting Subnet '{subnet['SubnetId']}'")
        client.delete_subnet(SubnetId=subnet['SubnetId'])

    for vpce in client.describe_vpc_endpoints(Filters=[{'Name': 'vpc-id','Values': [vpc]}])['VpcEndpoints']:
        logger.info(f"Deleting VPC Endpoint '{vpce['VpcEndpointId']}'")
        client.delete_vpc_endpoints(VpcEndpointIds=[vpce['VpcEndpointId']])

    logger.info(f"Deleting VPC '{vpc}'")
    client.delete_vpc(VpcId=vpc)

    logger.info("Cleaned up and rolled out! 😊")
if __name__ == '__main__':
    main()