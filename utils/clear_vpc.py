import logging
from datetime import date, datetime
import botocore
import boto3
import time

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
    tic = time.perf_counter()
    logger.info("Initiate AWS connections from Remove VPC.")
    session = boto3.Session()
    client = boto3.client('ec2')
    ec2 = boto3.resource('ec2')

    # vpc = 'vpc-01d6840cc8e27092c'
    vpc = input("Enter VPC ID: ")

    # for instance in client.describe_instances(Filters=[{'Name': 'vpc-id','Values': [vpc]}])['Reservations'][0]['Instances']:
    #     logger.info(f"Deleting Instance '{instance['InstanceId']}'")
    #     client.terminate_instances(InstanceIds=[instance['InstanceId']])


    nat_4_wait = None
    for nat in client.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [vpc]}])['NatGateways']:
        logger.info(f"Deleting NAT Gatewaty '{nat['NatGatewayId']}'")
        client.delete_nat_gateway(NatGatewayId=nat['NatGatewayId'])
        nat_4_wait = nat['NatGatewayId']

    logger.info("Waiting for last NAT Gateway to be deleted...")
    waiter = client.get_waiter('nat_gateway_deleted')
    waiter.wait(NatGatewayIds=[nat_4_wait])

    toc = time.perf_counter()
    print(f"NAT Deleted in {toc - tic:0.4f} seconds")

    for eip in client.describe_addresses()['Addresses']:
        logger.info(f"Elastic IP {eip['PublicIp']} is not associated, releasing")
        client.release_address(AllocationId=eip['AllocationId'])


    for ig in client.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id','Values': [vpc]}])['InternetGateways']:
        logger.info(f"Deleting Internet Gateway '{ig['InternetGatewayId']}'")
        client.detach_internet_gateway(InternetGatewayId=ig['InternetGatewayId'], VpcId=vpc)
        client.delete_internet_gateway(InternetGatewayId=ig['InternetGatewayId'])

    for scgr in client.describe_security_groups(Filters=[{'Name': 'vpc-id','Values': [vpc]}])['SecurityGroups']:
        logger.info(f"Deleting Security Group '{scgr['GroupName']}'")
        client.delete_security_group(GroupId=scgr['GroupId'])

    for rt in client.describe_route_tables(Filters=[{'Name': 'vpc-id','Values': [vpc]}])['RouteTables']:
        logger.info(rt)
        logger.info(f"Deleting Route Table '{rt['RouteTableId']}'")
        for rtb_assoc in rt['Associations']:
            if rtb_assoc['Main'] == False:
                client.disassociate_route_table(AssociationId=rtb_assoc['RouteTableAssociationId'])
        client.delete_route_table(RouteTableId=rt['RouteTableId'])

    for subnet in client.describe_subnets(Filters=[{'Name': 'vpc-id','Values': [vpc]}])['Subnets']:
        logger.info(f"Deleting Subnet '{subnet['SubnetId']}'")
        client.delete_subnet(SubnetId=subnet['SubnetId'])

    for vpce in client.describe_vpc_endpoints(Filters=[{'Name': 'vpc-id','Values': [vpc]}])['VpcEndpoints']:
        logger.info(f"Deleting VPC Endpoint '{vpce['VpcEndpointId']}'")
        client.delete_vpc_endpoints(VpcEndpointIds=[vpce['VpcEndpointId']])

    logger.info(f"Deleting VPC '{vpc}'")
    client.delete_vpc(VpcId=vpc)
    toc = time.perf_counter()
    print(f"VPC Deleted in {toc - tic:0.4f} seconds")

    logger.info("Cleaned up and rolled out! 😊")
if __name__ == '__main__':
    main()