# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from operator import attrgetter
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import tcp
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types
from ryu.ofproto import ofproto_v1_3_parser
from ryu.controller import dpset
from ryu.controller.handler import HANDSHAKE_DISPATCHER
from ryu.lib import hub

import random
import csv
import os
import socket
from threading import Thread, Event
import time

#   packet counters for load balancing of controllers
packet_in_counter_c1 = 0
packet_in_counter_c2 = 0
last_packet_in_counter_c1 = 0
last_packet_in_counter_c2 = 0

#   Declaring event to run TCP thread
event = Event()

# Creating csv files to store packet_in counter for each controller
if os.path.isfile('./packet_in_counter_1.csv'):
    print('packet_in_counter_1 exists')
else:
    print('create packet_in_counter_1.csv file')
    with open('packet_in_counter_1.csv', 'w') as csv_file:
        csv_file.write('')
        csv_file.close()

if os.path.isfile('./packet_in_counter_2.csv'):
    print('packet_in_counter_2 exists')
else:
    print('create packet_in_counter_2.csv file')
    with open('packet_in_counter_2.csv', 'w') as csv_file:
        csv_file.write('')
        csv_file.close()

# Storing initial roles of the controller in a file, to be ued from GUI
with open('c1_role.csv', 'w') as file:
    file.write(str(['MASTER', 'SLAVE']))
    file.close()


class SimpleSwitch13_c1(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13_c1, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.gen_id = 0
        self.role_string_list = ['nochange', 'equal', 'master', 'slave', 'unknown']
        self.datapath = []
        self.monitor_thread = hub.spawn(self._monitor)
        #   Initial roles of C1 controller
        self.role = ['MASTER', 'SLAVE']
        self.tcp_connection_on = True
        # Initial bandwidth of the links
        self.bandwidth_list = [120000, 120000, 120000, 120000, 120000]
        self.counter = 0
        self.bandwidth_string = ""
        self.bw_exceeded = False
        self.bandwidth_available = True

    #   Creating TCP socket fot the controller synchronization
    def open_client(self, event):
        TCP_IP = '127.0.0.1'
        TCP_PORT1 = 50501
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            client.connect((TCP_IP, TCP_PORT1))
        except:
            print("Connection failed")
        print("Controller 1 TCP opened succesfully")
        while True:
            #   Data is send via TCP in form of bytearray
            bandwidth_string = ','.join(str(e) for e in self.bandwidth_list)
            b = bytearray()
            b.extend(map(ord, bandwidth_string))
            # time.sleep(0.8)
            client.sendall(b)
            #   Receiving data from controller C2
            data = client.recv(1024)
            self.bandwidth_string = data
            #   If data is not received the other controller has failed
            if not data:
                self.tcp_connection_on = False
                break

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        #   Storing datapath of all the switches of topology
        datapath = ev.msg.datapath
        self.datapath.append(datapath)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    #   Adding flows rules to flow tables
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id, priority=priority, match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)
        datapath.send_msg(mod)

    #   Generating error messages in case of controller role conflict
    @set_ev_cls(ofp_event.EventOFPErrorMsg,[HANDSHAKE_DISPATCHER, CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def on_error_msg(self, ev):
        msg = ev.msg
        print("Receive a error message:", msg)

    #   Initial role assignment during dpset.EventDP
    @set_ev_cls(dpset.EventDP, MAIN_DISPATCHER)
    def on_dp_change(self, ev):
        if ev.enter:
            dp = ev.dp
            dpid = dp.id
            ofp = dp.ofproto
            ofp_parser = dp.ofproto_parser
            #   Role of the controllers depends on the dpid of the switches
            if dpid == 1:
                self.send_role_request(dp, ofp.OFPCR_ROLE_MASTER, self.gen_id)
            if dpid == 2:
                self.send_role_request(dp, ofp.OFPCR_ROLE_SLAVE, self.gen_id)

    #   Getting which role is assigned from the switches avery time a OFPRoleRequest is generated
    #   Switch -> controller
    @set_ev_cls(ofp_event.EventOFPRoleReply, MAIN_DISPATCHER)
    def on_role_reply(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        role = msg.role

        # unknown role
        if role < 0 or role > 3:
            role = 4
        print('')
        print(" ROLE REPLY switch %d->controller: %s" % (dp.id, self.role_string_list[role]))
        print("generation:", msg.generation_id)

    #   Sending OFPRoleRequest from controller -> switch
    def send_role_request(self, datapath, role, gen_id):
        ofp_parser = datapath.ofproto_parser
        print ("send a role change request")
        print ("role: ", self.role_string_list[role], "gen_id: ", gen_id)
        msg = ofp_parser.OFPRoleRequest(datapath, role, gen_id)
        datapath.send_msg(msg)

    #   Drop the flow in case bandwidth has exceeded
    def drop_flow(self, src, dst, datapath):
        ofproto = datapath.ofproto
        match = ofproto_v1_3_parser.OFPMatch(eth_src=src, eth_dst=dst)
        # Default action is to drop, hence, we can leave it empty
        actions = []
        highest_prio = 65535
        inst = [datapath.ofproto_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        msg_in = datapath.ofproto_parser.OFPFlowMod(datapath, priority=highest_prio, command=ofproto.OFPFC_ADD, match=match, instructions=inst)

    #   Remove any existing flows between two hosts if bandwidth has exeeded
    def remove_flow(self, src, dst, datapath):
        ofproto = datapath.ofproto
        match = ofproto_v1_3_parser.OFPMatch(eth_src=src, eth_dst=dst)
        # Default action is to drop, hence, we can leave it empty
        actions = []
        highest_prio = 65534
        inst = [datapath.ofproto_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        msg_in = datapath.ofproto_parser.OFPFlowMod(datapath, priority=highest_prio, command=ofproto.OFPFC_DELETE, match=match, instructions=inst)

    #   Check if bandwidth is exceeded
    def bw_limit_exceeded(self, index_list, src, dst, datapath):
        #   Get the list of bandwidth from the synchronized controllers
        bw_list_intermediate_str = self.bandwidth_string.split(',')
        bw_list_intermediate_int = []
        for i in bw_list_intermediate_str:
            bw_list_intermediate_int.append(int(i))
        if bw_list_intermediate_int == [120000, 120000, 120000, 120000, 120000]:
            bw_list_intermediate_int = self.bandwidth_list

        #   Check if bandwidth will exceed in certain links if we send the flow
        for i in index_list:
            print("Working!!!!!!!!!! bw_list_intermediate_int", bw_list_intermediate_int)
            if (bw_list_intermediate_int[i] - 100000) < 0:
                self.bw_exceeded = True
                print ("self.bw_exceeded!!!!!", self.bw_exceeded)

        #   If bandwidth will not exceed decrease the values for every link the flow will pass
        if self.bw_exceeded == False:
            print ("self.bw_exceeded !!!!!", self.bw_exceeded)
            print("Original bandwidth before deduction!!!!! self.bandwidth_list", self.bandwidth_list)
            for i in index_list:
                bw_list_intermediate_int[i] = bw_list_intermediate_int[i] - 100000
            self.bandwidth_list = bw_list_intermediate_int
            print("Remaining bandwidth after deduction!!!!! self.bandwidth_list", self.bandwidth_list)

        #   If bandwidth is not enough drop the flow and remove the flow rules from the flow table
        else:
            self.drop_flow(src, dst, datapath)
            self.remove_flow(src, dst, datapath)

    def _monitor(self):
        global global_timer
        global last_packet_in_counter_c1
        global last_packet_in_counter_c2
        global_timer = 0
        #   Starting the thread for TCP communication
        thread1 = Thread(target=self.open_client, args=(event,))
        thread1.start()
        # Setting the threshold to switch the controllers for load balancing
        thres_packet_in_rate = 20

        while True:
            hub.sleep(5)
            global_timer = global_timer + 5
            print('Current time is {}'.format(global_timer))
            self.counter = self.counter + 1
            print ("self.counter!!!!!!!!!!!!!!!!", self.counter)
            if (self.counter % 5 == 0):
                self.bandwidth_list = [120000, 120000, 120000, 120000, 120000]

            #   When one of the controllers fails the other becomes the master of all the switches
            if self.tcp_connection_on == False:
                if self.role != ['MASTER', 'MASTER']:
                    for datapath in self.datapath:
                        self.send_role_request(datapath, datapath.ofproto.OFPCR_ROLE_MASTER, self.gen_id)
                    self.role = ['MASTER', 'MASTER']
                    #   Updating role files for GUI
                    f = open("c1_role.csv", "w")
                    f.seek(0)
                    f.write(str(self.role))
                    f.close()
            #   Load balancing control plane
            else:
                list_read_1 = []
                list_read_2 = []
                #   Reading from the files that store packet_in counters
                if os.path.getsize('packet_in_counter_1.csv') > 0 and os.path.getsize('packet_in_counter_2.csv') > 0:
                    f1 = open('packet_in_counter_1.csv')
                    for x in f1:
                        list_read_1.append(x)
                    f2 = open('packet_in_counter_2.csv')
                    for x in f2:
                        list_read_2.append(x)
                    # print list_str
                    packet_in_ct_c1_str_curr = list_read_1[0]
                    packet_in_ct_c2_str_curr = list_read_2[0]

                    if packet_in_ct_c1_str_curr.isdigit() == False or packet_in_ct_c2_str_curr.isdigit() == False:
                        print("Packet_in count not decodable, continue")
                        continue

                    packet_in_counter_c1_curr = int(packet_in_ct_c1_str_curr)
                    packet_in_counter_c2_curr = int(packet_in_ct_c2_str_curr)
                    print("packet_in_counter_c1_curr, packet_in_counter_c2_curr", packet_in_counter_c1_curr, packet_in_counter_c2_curr)
                    #   Getting number of packet_ins for the last second
                    packet_count_last_second_c1 = packet_in_counter_c1_curr - last_packet_in_counter_c1
                    packet_count_last_second_c2 = packet_in_counter_c2_curr - last_packet_in_counter_c2
                    # packet_count_last_second_c2 = int(q) - last_packet_in_counter_c2
                    print("packet_count_last_second_c1, packet_count_last_second_c2", packet_count_last_second_c1, packet_count_last_second_c2)

                    #   Checking if there is an overloaded controller and switching controller ro
                    if abs(packet_count_last_second_c1 - packet_count_last_second_c2) > thres_packet_in_rate:
                        if (packet_count_last_second_c1 > packet_count_last_second_c2):
                            print('S1 will choose C2 as master')
                            self.role = ['SLAVE', 'SLAVE']
                            f = open("c1_role.csv", "w")
                            f.seek(0)
                            f.write(str(self.role))
                            f.close()
                            for datapath in self.datapath:
                                self.send_role_request(datapath, datapath.ofproto.OFPCR_ROLE_SLAVE, self.gen_id)

                        elif (packet_count_last_second_c1 < packet_count_last_second_c2):
                            print('S2 will choose C1 as master')
                            self.role = ['MASTER', 'MASTER']
                            #   Updating role files for GUI
                            f = open("c1_role.csv", "w")
                            f.seek(0)
                            f.write(str(self.role))
                            f.close()
                            for datapath in self.datapath:
                                self.send_role_request(datapath, datapath.ofproto.OFPCR_ROLE_MASTER, self.gen_id)

                    #   Resetting controller roles to initial state
                    elif abs(packet_count_last_second_c1 - packet_count_last_second_c2) <= thres_packet_in_rate:
                        print("C1 to remain the controller of S1 OR C2 to remain the controller of S2")
                        print ("self.role !!!!!!!!", self.role)
                        if (self.role == ['SLAVE', 'SLAVE'] or self.role == ['MASTER', 'MASTER'] or self.role == [
                            'SLAVE', 'MASTER']):
                            self.role = ['MASTER', 'SLAVE']
                            #   Updating role files for GUI
                            f = open("c1_role.csv", "w")
                            f.seek(0)
                            f.write(str(self.role))
                            f.close()
                            for datapath in self.datapath:
                                if datapath.id == 1:
                                    self.send_role_request(datapath, datapath.ofproto.OFPCR_ROLE_MASTER, self.gen_id)
                                if datapath.id == 2:
                                    self.send_role_request(datapath, datapath.ofproto.OFPCR_ROLE_SLAVE, self.gen_id)

                    last_packet_in_counter_c1 = packet_in_counter_c1_curr
                    last_packet_in_counter_c2 = packet_in_counter_c2_curr

                else:
                    print("1 or both files empty")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        global packet_in_counter_c1, packet_in_counter_c2
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        #   Increasing the counter every time a packet in comes
        packet_in_counter_c1 = packet_in_counter_c1 + 1
        #   Updating packet_in counter files
        f = open("packet_in_counter_1.csv", "r+b")
        f.seek(0)
        f.write(str(packet_in_counter_c1))
        f.close()

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.logger.info("packet in switch %s %s %s %s count %d", dpid, src, dst, in_port, packet_in_counter_c1)

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        #   Excluding ARP packet_ins from bandwidth reservation
        if (out_port != ofproto.OFPP_FLOOD):
            #   Checking for the specified controller domain hosts for bandwidth reservation
            if self.role == ['MASTER', 'SLAVE']:
                if (src == '00:00:00:00:00:01' and dst == '00:00:00:00:00:02') or (dst == '00:00:00:00:00:01' and src == '00:00:00:00:00:02'):
                    print ("h1-h2/h2-h1 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    #   Index list to indicate which links bandwidth will be checked and decreased
                    index_list = [0, 1]
                    self.bw_limit_exceeded(index_list, src, dst, datapath)
                elif (src == '00:00:00:00:00:01' and dst == '00:00:00:00:00:03'):
                    print ("h1-h3 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    index_list = [0, 2, 4]
                    self.bw_limit_exceeded(index_list, src, dst, datapath)
                elif (src == '00:00:00:00:00:01' and dst == '00:00:00:00:00:04'):
                    print ("h1-h4 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! src, dst", src, dst)
                    index_list = [0, 3, 4]
                    self.bw_limit_exceeded(index_list, src, dst, datapath)
                elif (src == '00:00:00:00:00:02' and dst == '00:00:00:00:00:03'):
                    print ("h2-h3 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    index_list = [1, 2, 4]
                    self.bw_limit_exceeded(index_list, src, dst, datapath)
                elif (src == '00:00:00:00:00:02' and dst == '00:00:00:00:00:04'):
                    print ("h2-h4 !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    index_list = [1, 3, 4]
                    self.bw_limit_exceeded(index_list, src, dst, datapath)

            #   Checking for all the hosts in topology in case it is the only controller running
            elif self.role == ['MASTER', 'MASTER']:
                if (src == '00:00:00:00:00:01' and dst == '00:00:00:00:00:02') or (dst == '00:00:00:00:00:01' and src == '00:00:00:00:00:02'):
                    index_list = [0, 1]
                    self.bw_exceeded = self.bw_limit_exceeded(index_list, src, dst, datapath)
                elif (src == '00:00:00:00:00:01' and dst == '00:00:00:00:00:03') or (dst == '00:00:00:00:00:01' and src == '00:00:00:00:00:03'):
                    index_list = [0, 2, 4]
                    self.bw_exceeded = self.bw_limit_exceeded(index_list, src, dst, datapath)
                elif (src == '00:00:00:00:00:01' and dst == '00:00:00:00:00:04') or (dst == '00:00:00:00:00:01' and src == '00:00:00:00:00:04'):
                    index_list = [0, 3, 4]
                    self.bw_exceeded = self.bw_limit_exceeded(index_list, src, dst, datapath)
                elif (src == '00:00:00:00:00:02' and dst == '00:00:00:00:00:03') or (dst == '00:00:00:00:00:02' and src == '00:00:00:00:00:03'):
                    index_list = [1, 2, 4]
                    self.bw_exceeded = self.bw_limit_exceeded(index_list, src, dst, datapath)
                elif (src == '00:00:00:00:00:02' and dst == '00:00:00:00:00:04') or (dst == '00:00:00:00:00:02' and src == '00:00:00:00:00:04'):
                    index_list = [1, 3, 4]
                    self.bw_exceeded = self.bw_limit_exceeded(index_list, src, dst, datapath)
                elif (src == '00:00:00:00:00:03' and dst == '00:00:00:00:00:04') or (dst == '00:00:00:00:00:03' and src == '00:00:00:00:00:04'):
                    index_list = [2, 3]
                    self.bw_exceeded = self.bw_limit_exceeded(index_list, src, dst, datapath)

        #   Excluding host 5 and 6 from bandwidth reservation, because they are used to generate load for load balanicng task
        if self.bw_exceeded and ((src == '00:00:00:00:00:01' or src == '00:00:00:00:00:02' or src == '00:00:00:00:00:03' or src == '00:00:00:00:00:04') and (dst == '00:00:00:00:00:01' or dst == '00:00:00:00:00:02' or dst == '00:00:00:00:00:03' or dst == '00:00:00:00:00:04')):
            print ("BW exceeded, discarding flow !!!!!")
        else:
            if ((src == '00:00:00:00:00:05' or src == '00:00:00:00:00:06') and (dst == '00:00:00:00:00:05' or dst == '00:00:00:00:00:06')):
                print ("h5 - h6 ping transfer, no flow rule inserted, no bandwidth check")
            else:
                print ("BW NOT exceeded, proceeding to install flow rule !!!!!")

            actions = [parser.OFPActionOutput(out_port)]
            data = None
            if (src == '00:00:00:00:00:05' or dst == '00:00:00:00:00:05'):
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data

                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions, data=data)
                datapath.send_msg(out)

            else:
                # install a flow to avoid packet_in next time
                if out_port != ofproto.OFPP_FLOOD:
                    match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
                    # verify if we have a valid buffer_id, if yes avoid to send both
                    # flow_mod & packet_out
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                        self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                        return
                    else:
                        self.add_flow(datapath, 1, match, actions)

                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data

                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                          in_port=in_port, actions=actions, data=data)
                datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no

        ofproto = msg.datapath.ofproto
        if reason == ofproto.OFPPR_ADD:
            self.logger.info("port added %s", port_no)
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.info("port deleted %s", port_no)
        elif reason == ofproto.OFPPR_MODIFY:
            self.logger.info("port modified %s", port_no)
        else:
            self.logger.info("Illeagal port state %s %s", port_no, reason)
