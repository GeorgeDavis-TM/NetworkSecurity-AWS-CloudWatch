#!/usr/bin/python3
import json
import urllib3
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from tabulate import tabulate

c1nsUrl = "https://cloudone.trendmicro.com/api/network"

f = open("config.json", "r+")
configObj = json.loads(f.read())
f.close()

headers = {
    "Content-Type": "application/json",
    "api-secret-key": configObj["c1nsApiKey"],
    "api-version": "v1"
}

def getAppliances():
    http = urllib3.PoolManager()
    r = http.request("GET", c1nsUrl + "/appliances", headers=headers)
    return json.loads(r.data)

def selectAppliance(appliancesDict):
    tempApplList = []
    tempListItemHeaders = ["ID", "InstanceId", "HostName", "Provider", "Provider Account Id", "Region"]
    tempApplList.append(tempListItemHeaders)
    for appliance in appliancesDict["appliances"]:
        tempListItem = []
        tempListItem.append(appliance["ID"])
        tempListItem.append(appliance["instanceId"])
        tempListItem.append(appliance["hostName"])
        tempListItem.append(appliance["provider"])
        for tempListItemProviderMetaItem in appliance["providerMetadata"]:
            if tempListItemProviderMetaItem["key"] == "accountId":
                tempListItem.append(tempListItemProviderMetaItem["value"])
        for tempListItemProviderMetaItem in appliance["providerMetadata"]:
            if tempListItemProviderMetaItem["key"] == "region":
                tempListItem.append(tempListItemProviderMetaItem["value"])

        tempApplList.append(tempListItem)
    print("\nList of Network Security Appliances in your Cloud One account -")
    print("\n" + tabulate(tempApplList, headers="firstrow"))

    applianceId = input('\nChoose the Network Security Appliance to configure from the list. Enter the Appliance ID - ')

    print("\n\nAppliance Selected - ")
    tempApplList = []
    tempListItemHeaders = ["ID", "InstanceId", "HostName", "Provider", "Version"]
    tempApplList.append(tempListItemHeaders)
    for appliance in appliancesDict["appliances"]:
        if str(appliance["ID"]) == applianceId:
            tempListItem = []
            tempListItem.append(appliance["ID"])
            tempListItem.append(appliance["instanceId"])
            tempListItem.append(appliance["hostName"])
            tempListItem.append(appliance["provider"])
            tempListItem.append(appliance["tosVersion"])
            tempApplList.append(tempListItem)
    print("\n" + tabulate(tempApplList, headers="firstrow"))
    
    confirmation = input('\nConfirm selection? (Y/n) - ')

    if confirmation.lower() == "y":
        for appliance in appliancesDict["appliances"]:
            if str(appliance["ID"]) == applianceId:
                if appliance["tosVersion"]:
                    applVersionList = appliance["tosVersion"].split(".")
                    if int(applVersionList[0]) >= 2020 and int(applVersionList[1]) >= 10 and int(applVersionList[2]) >= 0:
                        return appliance
                    else:
                        print("\n\nIncompatible version. Unable to configure CloudWatch Logs using APIs.")
    else:
        print("\n\nExiting..\n\n")

def isAWSInstanceRunning(regionName, applianceDict):
    config = Config(
        region_name = regionName
    )
    ec2Client = boto3.client('ec2', config=config)
    ec2ResponseDict = ec2Client.describe_instance_status(
        InstanceIds=[
            applianceDict["instanceId"]
        ],
        IncludeAllInstances=True
    )
    if ec2ResponseDict["InstanceStatuses"][0]["InstanceState"]["Name"] == "running":
        return True
    else:
        print("\n\nInstance ID " + applianceDict["instanceId"] + " is unreachable or maybe be turned off. Please check and try again.")
        print("\n\tInstance URL - https://" + regionName + ".console.aws.amazon.com/ec2/v2/home?region=" + regionName + "#Instances:search=" + applianceDict["instanceId"])
        print("\n\nExiting..\n\n")
        return False

def handleCloudformationStacks(regionName, stackName):
    config = Config(
        region_name = regionName
    )
    cfClient = boto3.client('cloudformation', config=config)

    allowedCloudformationStackStates = ["CREATE_COMPLETE", "UPDATE_COMPLETE"]

    try:
        cfResponseDict = cfClient.describe_stacks(
            StackName=stackName
        )
        if cfResponseDict['Stacks'][0]['StackStatus'] in allowedCloudformationStackStates:
            print("\n\nAWS CloudFormation Stack Name '" + stackName + "' already exists. Please check your existing stack for existing CloudWatch LogGroup Name or use a different stack name in the config.json file")
            print("\n\nExiting..\n\n")
            return False
        else:
            print("\n\nAWS CloudFormation Stack Name '" + stackName + "' already exists in unexpected state, state other than CREATE_COMPLETE or UPDATE_COMPLETE. Please check your existing stack for existing CloudWatch LogGroup Name or use a different stack name in the config.json file")
            print("\n\nExiting..\n\n")
            return False
    except ClientError as err:
        if err.response["Error"]["Code"] == "ValidationError":
            return True
        else:
            print("\n\nError: " + str(err))
            print("\n\nExiting..\n\n")
            return False

def createCloudWatchLogGroup(regionName, stackName):
    cf = open('deploy_cloudformation_template.json', 'r+')
    cfBody = cf.read()
    cf.close()

    config = Config(
        region_name = regionName
    )
    cfClient = boto3.client('cloudformation', config=config)

    try:
        cfResponseDict = cfClient.validate_template(
            TemplateBody=cfBody
        )
    
        cfResponseDict = cfClient.create_stack(
            StackName=stackName,
            TemplateBody=cfBody,
            Tags=[
                {
                    'Key': 'Product',
                    'Value': 'TrendMicroCloudOneNetworkSecurity'
                },
                {
                    'Key': 'Owner',
                    'Value': 'TrendMicro'
                }
            ],
            EnableTerminationProtection=True|False
        )

        cfWaiter = cfClient.get_waiter('stack_create_complete')
        cfWaiter.wait(
            StackName=stackName,
            WaiterConfig={
                'Delay': 10,
                'MaxAttempts': 30
            }
        )

        cfResponseDict = cfClient.describe_stack_resources(
            StackName=stackName,
            LogicalResourceId='C1NSCloudWatchLogs'
        )

        print("\n\tResource Creation Status - ", cfResponseDict["StackResources"][0]["ResourceStatus"])
        print("\n\tCloudFormation Stack Name Used - ", cfResponseDict["StackResources"][0]["StackName"])
        print("\n\tCloudFormation Stack ID Used - ", cfResponseDict["StackResources"][0]["StackId"])
        print("\n\tResource URL - https://" + regionName + ".console.aws.amazon.com/cloudwatch/home?region=" + regionName + "#logStream:group=" + cfResponseDict["StackResources"][0]["PhysicalResourceId"])

        return cfResponseDict["StackResources"][0]["PhysicalResourceId"]
    except ClientError as err:
        if err.response["Error"]["Code"] == "ValidationError":
            print("\n\nError: AWS CloudFormation Template invalid after modifications. Please check for proper JSON and refer AWS CloudFormation documentation before retrying.")
            print("\n\nExiting..")
            return ""

def postApplianceCloudWatchLogConfig(regionName, cloudWatchLogGroupName, applianceDict): 
    data = {
        "logTypes": [
            {
                "logGroupName": cloudWatchLogGroupName,
                "logStreamName": "audit_" + str(applianceDict["instanceId"]),
                "logName": "audit",
                "enable": False
            },
            {
                "logGroupName": cloudWatchLogGroupName,
                "logStreamName": "host_" + str(applianceDict["instanceId"]),
                "logName": "host",
                "enable": False
            },
            {
                "logGroupName": cloudWatchLogGroupName,
                "logStreamName": "ipsAlert_" + str(applianceDict["instanceId"]),
                "logName": "ipsAlert",
                "enable": False
            },
            {
                "logGroupName": cloudWatchLogGroupName,
                "logStreamName": "ipsBlock_" + str(applianceDict["instanceId"]),
                "logName": "ipsBlock",
                "enable": False
            },
            {
                "logGroupName": cloudWatchLogGroupName,
                "logStreamName": "quarantine_" + str(applianceDict["instanceId"]),
                "logName": "quarantine",
                "enable": False
            },
            {
                "logGroupName": cloudWatchLogGroupName,
                "logStreamName": "reputationAlert_" + str(applianceDict["instanceId"]),
                "logName": "reputationAlert",
                "enable": False
            },
            {
                "logGroupName": cloudWatchLogGroupName,
                "logStreamName": "reputationBlock_" + str(applianceDict["instanceId"]),
                "logName": "reputationBlock",
                "enable": False
            },
            {
                "logGroupName": cloudWatchLogGroupName,
                "logStreamName": "system_" + str(applianceDict["instanceId"]),
                "logName": "system",
                "enable": False
            }
        ],
        "next": None,
        "totalCount": 8
    }
    
    logConf = open("cloudwatchlogconfig.json", "r+")
    logConfObj = json.loads(logConf.read())
    logConf.close()

    for logItem in logConfObj["logTypes"]:
        for logConfig in data["logTypes"]:
            if logConfig["logName"] == logItem["logName"]:
                logConfig["enable"] = logItem["enable"]

    http = urllib3.PoolManager()
    r = http.request("POST", c1nsUrl + "/appliances/" + str(applianceDict["ID"]) + "/cloudwatchlogconfig", headers=headers, body=json.dumps(data))

    if r.status == 200:
        print("\n\nSuccess: NVSA logs from " + str(applianceDict["instanceId"]) + " are configured to relay to AWS CloudWatch Log Group: " + cloudWatchLogGroupName)
        print("\n\tAWS CloudWatch Log Group URL - https://" + regionName + ".console.aws.amazon.com/cloudwatch/home?region=" + regionName + "#logStream:group=" + cloudWatchLogGroupName)
        print("\n\nExiting..\n\n")

def main():
    print("\n\nCloud One Network Security - AWS CloudWatch Log Configurator tool\n==================================================================\n")
    envAppliances = getAppliances()
    selectedApplianceDict = selectAppliance(envAppliances)
    if selectedApplianceDict:
        if selectedApplianceDict["provider"] == "AWS":
            regionName = ""
            stackName = configObj["stackName"]
            for metadata in selectedApplianceDict["providerMetadata"]:
                if metadata["key"] == "region":
                    regionName = metadata["value"]
            if handleCloudformationStacks(regionName, stackName):
                if isAWSInstanceRunning(regionName, selectedApplianceDict):
                    print("\nCreating an AWS CloudWatch Log Group to store Cloud One Network Security logs...")
                    cloudWatchLogGroupName = createCloudWatchLogGroup(regionName, stackName)
                    if cloudWatchLogGroupName:
                        postApplianceCloudWatchLogConfig(regionName, cloudWatchLogGroupName, selectedApplianceDict)
        else:
            print("\n\n" + selectedApplianceDict["provider"] + " APIs are not supported by this tool at this moment. Please raise an issue on the GitHub repository to request for support along with a screenshot of this error or provider information.")
            print("\n\nExiting..\n\n")
    
if __name__ == "__main__":
    main()
