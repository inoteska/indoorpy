#! /bin/bash
SERIAL=`cat /proc/cpuinfo | grep -i '^serial' | grep -Eo '[a-fA-F0-9]{16}$'`
DAT=$(date "+%Y-%m-%d")
IP_ADDR=`hostname -I`
INET=`cat /etc/network/interfaces | grep "eth0 inet" | awk '{print $4}'`
NETMASK=`ifconfig eth0 | grep inet | awk '{print $4}' | sed 's/Mask://'`
BROADCAST=`ifconfig eth0 | grep inet | awk '{print $3}' | sed 's/Bcast://'`
GATEWAY=`netstat -rn | grep eth0 | awk '{if($1=="0.0.0.0") print $2}'`
NETWORK=`netstat -rn | grep eth0 | awk '{if($1!="0.0.0.0") print $1}'`
DNS=`cat /etc/resolv.conf | grep nameserver | awk 'NR==1 {print $2}'`

echo $DAT $SERIAL $INET $IP_ADDR $NETMASK $BROADCAST $GATEWAY $NETWORK $DNS