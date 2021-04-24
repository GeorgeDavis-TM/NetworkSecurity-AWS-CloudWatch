# NetworkSecurity-AWS-CloudWatchLogs Integration
Automation to configure Trend Micro Cloud One Network Security to push IPS logs to AWS CloudWatch Log Group

## Setup Instructions

Step 1: Create a Cloud One Workload Security API Key. Cloud One Network Security uses Workload Security API keys to authenticate API requests. Refer to the Workload Security documentation for steps to create this API key - https://cloudone.trendmicro.com/docs/workload-security/api-send-request/#create-an-api-key

Step 2: Replace the API key in `config.json` for `c1nsApiKey`

Step 3: Review the Log configuration in the `cloudwatchlogconfig.json` file

Step 4: Run the python script `cloud_one_network_security_logs_aws_cloudwatch_integration.py`


## How it works

The CloudFormation template creates the following resources -

- Amazon CloudWatch Log Group
    - Network Security sends event logs for various categories, like `audit`, `host`, `ipsAlert`, `ipsBlock`, `quarantine`, `reputationAlert`, `reputationBlock` and `system`.
    - The CloudWatch Log Group is encrypted by default.

The Python script ensures the following -

    - Retrieves the list of Network Security appliances configured to your Trend Micro Cloud One account
    - Provides a tabulated list to choose the Network Security appliance to configure
    - Check if a CloudFormation Stack already exists with the same Stack Name, pre-configured to receive logs from Network Security
    - Ensures the Network Security appliance or instance/VM is running
    - Runs the CloudFormation template discussed above to create a new log group destination for the Network Security logs
    - Calls Network Security APIs to configure log forwarding to the destination AWS CloudWatch Log Group 


## Contributing

If you encounter a bug or think of a useful feature, need support for other providers, find something confusing in the docs, please
**[Create a New Issue](https://github.com/GeorgeDavis-TM/NetworkSecurity-AWS-CloudWatchLogs/issues/new)**

 **PS.: Make sure to use the [Issue Template](https://github.com/GeorgeDavis-TM/NetworkSecurity-AWS-CloudWatchLogs/tree/master/.github/ISSUE_TEMPLATE)**

We :heart: pull requests. If you'd like to fix a bug or contribute to a feature or simply correct a typo, please feel free to do so.

If you're thinking of adding a new feature, consider opening an issue first to
discuss it to ensure it aligns to the direction of the project (and potentially
save yourself some time!).
