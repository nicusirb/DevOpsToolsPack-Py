#!/bin/bash

# Generate ssh key for Jenkins Agent
ssh-keygen -t rsa -f /tmp/jenkins_agent -N ""

sed -i "s|-JENKINS_AGENT_SSH_PUBKEY-|$(cat /tmp/jenkins_agent.pub)|" docker-compose.yaml
docker-compose up -d