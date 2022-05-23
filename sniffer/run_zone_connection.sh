#!/bin/bash
read -p "Enter device's Serial number: " sn
read -p "Enter number of Sniffers: " num
echo "Serial number: $sn Sniffers: $num"
python -m Connections.check_zone_connection $sn $num
#python -m Connections.check_zone_connection 1587497 2
read -t 300 -p "Press [Enter] to finish"
#read -p "Press [Enter] to finish"
