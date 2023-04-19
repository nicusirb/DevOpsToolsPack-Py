#!/bin/bash

# Generate ssh key for Jenkins Agent
ssh-keygen -t rsa -f ./.jenkins_agent -N ""
sed -i "s|-JENKINS_AGENT_SSH_PUBKEY-|$(cat ./.jenkins_agent.pub)|" "$(dirname $0)/docker-compose.yaml"
docker-compose -f "$(dirname $0)/docker-compose.yaml" up -d