#!/bin/bash
#
# Simple script to run the server with authbind on port 443. You may need to
# configure authbind to allow the user to bind to port 443. For example, you can
# run the following command to allow the current user to bind to port 443:
# sudo touch /etc/authbind/byport/443
# sudo chown $USER /etc/authbind/byport/443
# sudo chmod 755 /etc/authbind/byport/443
# After running this script, the server will be accessible on port 443.
#
# Also make sure iptables does not block incoming traffic on port 443. You can check this with:
# sudo iptables -L -n | grep 443
# 
# OCI defaults to blocking all incoming traffic, so you may need to add a rule to allow traffic on port 443. For example:
# sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
# Note that you may need to adjust the iptables rules based on your specific
# setup and security requirements. Always be cautious when modifying firewall
# rules to avoid exposing your server to unwanted traffic.
#

set -o xtrace
PORT=443 authbind --deep python3 server.py
