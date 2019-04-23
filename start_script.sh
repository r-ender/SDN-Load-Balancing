#!/bin/bash

rm packet_in_counter_1.csv 
rm packet_in_counter_2.csv 
sudo mn -c

gnome-terminal -e 'bash start_script2.sh' 
sleep 1
gnome-terminal -e 'bash start_script3.sh' 
sleep 1
sudo gnome-terminal -e 'bash start_script4.sh' 

#while-loop for updating the packet-counter of the GUI (updating packetcounters at runtime is not possible)
COUNTER=0
while [  $COUNTER -lt 3 ]; do
    timeout -k 0m 25s python testgui_v3.py 
    let COUNTER=COUNTER+1 
done

#don't update packet-counters any more, just leave the topology for updating the roles (with function "paintEvent" of GUI-code)
python testgui_v3.py


