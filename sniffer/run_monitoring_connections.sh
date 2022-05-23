#!/bin/bash
read -p "Enter device's Serial number or 0 if not specified: " sn
read -p "Enter number of Sniffers: " num
echo "Serial number: $sn Sniffers: $num"
python -m Connections.monitoring_connections $sn $num
read -t 300 -p "Press [Enter] to finish"
