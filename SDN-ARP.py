from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import packet, ether_types, ethernet, arp

# ofproto 在这个目录下，基本分为两类文件，一类是协议的数据结构定义，另一类是协议解析，也即数据包处理函数文件。

# Its like database that save the ip-mac table
arp_table = {"10.0.0.1": "00:00:00:00:00:01",
             "10.0.0.2": "00:00:00:00:00:02",
             "10.0.0.3": "00:00:00:00:00:03",
             "10.0.0.4": "00:00:00:00:00:04"
             }


class swich(app_manager):

    def __init__(self, *args, **kwargs):
        super(swich, self).__init__(*args, **kwargs)
        self.Mac_Port_Table = {}  # mac learn, change

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser
        match = ofproto_parser.OFPMatch()

        action = [ofproto_parser.OFPActionOutput(ofproto.OFPP_NORMAL,ofproto.OFPCML_NO_BUFFER)]  # (port,max)
        self.send_flow_mod(datapath, 0, match, action)

    def send_flow_mod(self, datapath, priority, match, actions,buffer_id=None):
        """"
            send flow table
        """
        ofproto = datapath.ofproto
        ofproto_parse = datapath.ofproto_parser

        inst = [ofproto_parse.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]
        if  buffer_id:
           Out = ofproto_parse.OFPFlowMod(
               priority=priority,
               buffer_id=buffer_id,
               match=match,
               instructions=inst,
           )
        else:
            Out = ofproto_parse.OFPFlowMod(
                priority=priority,
                match=match,
                instructions=inst,
            )
        datapath.send_msg(Out) #The controller sends this message to modify the flow table.

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.dpid
        self.Mac_Port_Table.setdefault(dpid, {})

        pkt = packet.Packet(msg.data)
        pkt_ethernet = pkt.get_protocol(ethernet.ethernet)
        if pkt_ethernet :
            dst_mac = pkt_ethernet.dst  #controller MAC
            src_mac = pkt_ethernet.src  #switch MAC
            self.Mac_Port_Table[dpid][src_mac] = in_port
        pkt_arp = pkt.get_protocol(arp.arp)
        if pkt_arp:
            print("datapath id: " + str(dpid))
            print("port: " + str(in_port))
            print("pkt_eth.dst: " + str(pkt_ethernet.dst))
            print("pkt_eth.src: " + str(pkt_ethernet.src))
            print("pkt_arp: " + str(pkt_arp))
            print("pkt_arp:src_ip: " + str(pkt_arp.src_ip))
            print("pkt_arp:dst_ip: " + str(pkt_arp.dst_ip))
            print("pkt_arp:src_mac: " + str(pkt_arp.src_mac))
            print("pkt_arp:dst_mac: " + str(pkt_arp.dst_mac))

            self.arp_process()

    def arp_process(self, datapath, pkt_ethernet, pkt_arp, in_port):
        
        # -------- Check database -------------------
        r = arp_table.get(pkt_arp.dst_ip)
        # ----------------------------
        if len(r) != 0:
            arp_resp = packet.Packet()  # Construct a packet
            arp_resp.add_protocol(ethernet.ethernet(
                dst=pkt_ethernet.src, #目的地址
                src=r, #发送地址
                ethertype=pkt_ethernet.ethertype
            ))  # define ethernet protocol
            arp_resp.add_protocol(arp.arp(
                opcode=arp.ARP_REPLY,  # arp reply
                # 发送地址
                src_mac=r,
                src_ip=pkt_arp.dst_ip,
                # 目的地址
                dst_mac=pkt_arp.src_mac,
                dst_ip=pkt_arp.src_ip
            ))  # define arp packet
            arp_resp.serialize()  # Encode a packet
            ofproto_parser = datapath.ofproto_parser

            ofproto = datapath.ofproto
            actions = [ofproto.OFPActionOutput(in_port)]
            Out = ofproto_parser.OFPPacketOut(datapath, in_port, actions,arp_resp)  # What is buffer_id???
            datapath.send_msg(Out)