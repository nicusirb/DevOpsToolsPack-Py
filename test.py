
import boto3
import json

## TO DO:
# Build IP Permissions Format from -> "0.0.0.0/0;172.18.20.15/32:22,0.0.0.0/0:80"

# def test(ip_permissions):
#     ec2_ip_permissions = {}
#     for x in ip_permissions.split(','):
#         ec2_ip_permissions.update(dict({'IpProtocol': 'tcp','FromPort': " + x.split(':')[1] + ",'ToPort': " + x.split(':')[1] + ",'IpRanges': [{'CidrIp': '" + str([y for y in x.split(':')[0].split(';')]) + "'}]}))
#         # print("{'IpProtocol': 'tcp','FromPort': " + x.split(':')[1] + ",'ToPort': " + x.split(':')[1] + ",'IpRanges': [{'CidrIp': '",[y for y in x.split(':')[0].split(';')],"'}]},")
#     # ip_permissions = "[" + ", ".join(ip_permissions) + "]"
#     print(ip_permissions)
#     print(ec2_ip_permissions)

def test2(ip_permissions):
    # print(f"Example:\n{'IpProtocol': 'tcp','FromPort': 22,'ToPort': 22,'IpRanges': [{'CidrIp': '0.0.0.0/0'},{'CidrIp': '1.0.0.0/0'}]}\n")
    
    # 0.0.0.0/0;172.18.20.15/32:22,0.0.0.0/0:80

    ec2_ip_permissions = []
    for x in ip_permissions.split(','):
        ip_ranges = []
        for y in x.split(':')[0].split(';'):
            ip_ranges.append({'CidrIp': y})
        ec2_ip_permissions.append({'IpProtocol': 'tcp','FromPort': x.split(':')[1],'ToPort': x.split(':')[1],'IpRanges': ip_ranges})
    print(f"Result:\n {ec2_ip_permissions}\n")

"""
[
    {'IpProtocol': 'tcp',
    'FromPort': 80,
    'ToPort': 80,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
    {'IpProtocol': 'tcp',
    'FromPort': 443,
    'ToPort': 443,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},               
    {'IpProtocol': 'tcp',
    'FromPort': 22,
    'ToPort': 22,
    'IpRanges': [{'CidrIp': '0.0.0.0/0'},{'CidrIp': '1.0.0.0/0'}]}
]
"""


if __name__ == '__main__':
    test2("0.0.0.0/0:22,0.0.0.0/0:80,0.0.0.0/0:443")