from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import packet, ether_types, ethernet, arp

#ofproto 在这个目录下，基本分为两类文件，一类是协议的数据结构定义，另一类是协议解析，也即数据包处理函数文件。

#Its like database that save the ip-mac table
arp_table = {"10.0.0.1": "00:00:00:00:00:01",
             "10.0.0.2": "00:00:00:00:00:02",
             "10.0.0.3": "00:00:00:00:00:03",
             "10.0.0.4": "00:00:00:00:00:04"
}

class A(app_manager):

    def __init__(self, *args, **kwargs):
        super(A, self).__init__(*args, **kwargs)
        self.mac_to_port = {}  #mac learn

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()

    def add_flow(self):
        pass

    def arp_process(self,datapath, eth, a, in_port):
        r = arp_table.get(a.dst_ip)
        arp_resp = packet.Packet() #Construct a packet
        arp_resp.add_protocol(ethernet.ethernet(
            dst="",
            src="",
            ethertype=""
        ))  # define ethernet protocol
        arp_resp.add_protocol(arp.arp(
            opcode=arp.ARP_REPLY, # arp reply
            src_mac='ff:ff:ff:ff:ff:ff',
            src_ip='0.0.0.0',
            dst_mac='ff:ff:ff:ff:ff:ff',
            dst_ip='0.0.0.0'
        )) # define arp packet
        arp_resp.serialize()# Encode a packet
        parser = datapath.ofproto_parser

        ofproto = datapath.ofproto
        actions = [ofproto.OFPActionOutput(ofproto.OFPP_FLOOD, 0)]
        Out = parser.OFPPacketOut(datapath, buffer_id,in_port, actions)    #What is buffer_id???
        datapath.send_msg(Out)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def apccept_packet_in(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        in_port = msg.match['in_port']

        pkt = packet.Packet(data=msg.data)
        pkt_ethernet = pkt.get_protocol(ethernet.ethernet)
        if  pkt_ethernet == ether_types.ETH_TYPE_LLDP:
            return
        #Check whether is it arp packet
        if pkt_ethernet.ether_types == ether_types.ETH_TYPE_ARP:
            a = pkt.get_protocol(arp.arp)
            self.arp_process(datapath,pkt_ethernet,a,in_port)
            return
