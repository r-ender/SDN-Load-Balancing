#!/usr/bin/python

import time
import sys
import socket
from threading import Event, Thread

from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info

import networkx as nx
from networkx.drawing.nx_agraph import write_dot, graphviz_layout
import matplotlib.pyplot as plt

event = Event()

def netTAR():
    label = {}	#empty dict
    G = nx.Graph()
    port1 = 6653
    port2 = 6699
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch)

    #controllers
    c1 = net.addController('c1', controller=RemoteController, ip="127.0.0.1", port=port1)
    G.add_node(c1,pos=(5,0))
    label[c1] = 'c1'
    c2 = net.addController('c2', controller=RemoteController, ip="127.0.0.1", port=port2)
    G.add_node(c2,pos=(15,0))
    label[c2] = 'c2'


    #hosts
    h1 = net.addHost( 'h1', mac = '00:00:00:00:00:01' )
    G.add_node(h1,pos=(3,-7))
    label[h1] = 'h1'
    h2 = net.addHost( 'h2', mac = '00:00:00:00:00:02' )
    G.add_node(h2,pos=(7,-7))
    label[h2] = 'h2'
    h3 = net.addHost( 'h3', mac = '00:00:00:00:00:03' )
    G.add_node(h3,pos=(13,-7))
    label[h3] = 'h3'
    h4 = net.addHost( 'h4', mac = '00:00:00:00:00:04' )
    G.add_node(h4,pos=(17,-7))
    label[h4] = 'h4'
    h5 = net.addHost( 'h5', mac = '00:00:00:00:00:05' )
    G.add_node(h5,pos=(5,-7))
    label[h5] = 'h5'
    h6 = net.addHost( 'h6', mac = '00:00:00:00:00:06' )
    G.add_node(h6,pos=(9,-7))
    label[h6] = 'h6'


    #switches
    s1 = net.addSwitch( 's1' )
    G.add_node(s1,pos=(5,-3))
    label[s1] = 's1'
    s2 = net.addSwitch( 's2' )
    G.add_node(s2,pos=(15,-3))
    label[s2] = 's2'

    #links
    s1.linkTo( h1 )
    s1.linkTo( h2 )
    s1.linkTo( h5 )
    s1.linkTo( h6 )
    s2.linkTo( h3 )
    s2.linkTo( h4 )
    s1.linkTo( s2 )

    #draw nodes,edges and labels
    controllers = [c1, c2]
    switchs = [s1,s2]
    hosts = [h1,h2,h3,h4,h5,h6]
    #
    G.add_edge(c1,s1)
    G.add_edge(c2,s2)
    G.add_edge(s1,s2)
    G.add_edge(s1,h1)
    G.add_edge(s1,h2)
    G.add_edge(s1,h5)
    G.add_edge(s1,h6)
    G.add_edge(s2,h3)
    G.add_edge(s2,h4)
    #
    pos=nx.get_node_attributes(G,'pos')
    nx.draw_networkx_nodes(G,pos=pos,nodelist=hosts, node_color='g',node_size=4000, alpha=1.0,node_shape='^')
    nx.draw_networkx_nodes(G,pos=pos,nodelist=switchs, node_color='b',node_size=1500, alpha=1.0,node_shape='s')
    nx.draw_networkx_nodes(G,pos=pos,nodelist=controllers, node_color='r',node_size=1500, alpha=1.0,node_shape='o')
    nx.draw_networkx_edges(G,pos=pos,width=3.0, alpha=0.8)
    nx.draw_networkx_edges(G,pos=pos,width=2.0,edgelist=[(c1,c2)], alpha=0.8,style='dashed')
    nx.draw_networkx_labels(G,pos,label,font_size=16)

    #plot topology
    plt.title('Multicontroller topoplogy',fontsize=30)
    plt.axis('off')
    plt.savefig("mult_ctrl_topo.png")


    #build and start mininet
    net.build()
    c1.start()
    c2.start()
    s1.start( [c1] )
    s2.start( [c2] )
    net.start()
    net.staticArp()
    CLI( net )


if __name__ == '__main__':
     setLogLevel( 'info' )
     netTAR()
