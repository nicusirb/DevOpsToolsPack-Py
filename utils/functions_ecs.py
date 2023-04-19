import botocore
import boto3
import json

def create_ecs_cluster(cluster_name):
    client = boto3.client('ecs')

    try:
        check = [x.split('/')[1] for x in client.list_clusters()['clusterArns']]
        if cluster_name in check:
            print(f"Cluster '{cluster_name}' already exists.")
            return client.describe_clusters(clusters=[cluster_name])
        else:
            raise IndexError
    except IndexError:
        print(f"Cluster '{cluster_name}' does not exists. Creating...")
        response = client.create_cluster(
            clusterName=cluster_name,
            tags=[
                {
                    'key': 'Project',
                    'value': 'DevOps Tools Pack'
                },
            ],
            settings=[
                {
                    'name': 'containerInsights',
                    'value': 'disabled'
                },
            ],
            configuration={
                'executeCommandConfiguration': {
                    'logging': 'DEFAULT',
                }
            },
            capacityProviders=[
                'FARGATE',
                'FARGATE_SPOT'
            ],
            serviceConnectDefaults={
                'namespace': cluster_name
            }
        )

        ## [Nice to have] TODO: Wait until cluster is ready.
        # client = boto3.client("emr")
        # waiter = client.get_waiter('step_complete')
        # waiter.wait(
        #     ClusterId=response['cluster']['clusterArn'],
        #     StepId='PROVISIONING',
        #     WaiterConfig={
        #         'Delay': 15,
        #         'MaxAttempts': 10
        #     }
        # )
        # print(waiter)


        return response
    return

def create_role_AmazonECSTaskExecutionRolePolicy():
    # Role needed when creating ECS Task Definition
    client = boto3.client('iam')

    if 'AmazonECSTaskExecutionRolePolicy' in [x['RoleName'] for x in client.list_roles()['Roles']]:
        print(f"Role 'AmazonECSTaskExecutionRolePolicy' already exists.")
        return

    response = client.create_role(
        Path='/',
        RoleName='AmazonECSTaskExecutionRolePolicy',
        AssumeRolePolicyDocument='{"Version": "2012-10-17","Statement": [{"Sid": "","Effect": "Allow","Principal": {"Service": "ecs-tasks.amazonaws.com"},"Action": "sts:AssumeRole"}]}',
        Description='Allows ECS tasks to call AWS services on your behalf.',
        MaxSessionDuration=3600,
        Tags=[
            {
                'Key': 'Project',
                'Value': 'DevOps Tools Pack'
            },
        ]
    )
    
    print(f"[Info] Role '{response['Role']['RoleName']}' created successfully.")
    print(f"            'role_id'  : '{response['Role']['RoleId']}'")
    return response

def main():
    client = boto3.client('ecs')

    cluster_name = "DevOps_Tools_Pack"
    
    # Create ECS Role
    create_role_AmazonECSTaskExecutionRolePolicy()

    # Create ECS Cluster
    # create_ecs_cluster(cluster_name)
    cluster_lcl = client.describe_clusters(clusters=[cluster_name])
    print(f"[Info] Cluster details:")
    print(f"            'clusterArn'          : '{cluster_lcl['clusters'][0]['clusterArn']}'")
    print(f"            'clusterName'         : '{cluster_lcl['clusters'][0]['clusterName']}'")
    print(f"            'status'              : '{cluster_lcl['clusters'][0]['status']}'")
    print(f"            'runningTasksCount'   : '{cluster_lcl['clusters'][0]['runningTasksCount']}'")
    print(f"            'pendingTasksCount'   : '{cluster_lcl['clusters'][0]['pendingTasksCount']}'")
    print(f"            'activeServicesCount' : '{cluster_lcl['clusters'][0]['activeServicesCount']}'")

    


if __name__ == '__main__':
    main()