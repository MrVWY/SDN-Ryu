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
        self.Mac_Port_Table = {}  # mac learn

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser
        match = ofproto_parser.OFPMatch(
            in_port = "",
            eth_dst = "",
        )

        action = [ofproto_parser.OFPActionOutput(ofproto.OFPP_NORMAL)]  # (port,max)
        self.send_flow_mod(datapath, 0, match, action)

    def send_flow_mod(self, datapath, priority, match, actions):
        """"
            send flow table
        """
        ofproto = datapath.ofproto
        ofproto_parse = datapath.ofproto_parser

        idle_timeout = hard_timeout = 0
        inst = [ofproto_parse.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]

        Out = ofproto_parse.OFPFlowMod(
            cookie="",
            cookie_mask="",
            table_id="",
            command="",
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
            priority=priority,
            buffer_id="",
            out_port="",
            out_group="",
            flags="",
            importance="",
            match=match,
            instructions=inst,
        )
        datapath.send_msg(Out) #The controller sends this message to modify the flow table.

    def arp_process(self, datapath, eth, a, in_port):
        # -------- Check database -------------------
        r = arp_table.get(a.dst_ip)
        # ----------------------------
        if len(r) != 0:
            arp_resp = packet.Packet()  # Construct a packet
            arp_resp.add_protocol(ethernet.ethernet(
                dst=eth.src, #目的地址
                src=r, #发送地址
                ethertype=eth.ethertype
            ))  # define ethernet protocol
            arp_resp.add_protocol(arp.arp(
                opcode=arp.ARP_REPLY,  # arp reply
                # 发送地址
                src_mac=r,
                src_ip=a.dst_ip,
                # 目的地址
                dst_mac=a.src_mac,
                dst_ip=a.src_ip
            ))  # define arp packet
            arp_resp.serialize()  # Encode a packet
            ofproto_parser = datapath.ofproto_parser

            ofproto = datapath.ofproto
            actions = [ofproto.OFPActionOutput(ofproto.OFPP_FLOOD)]  #OFPP_FLOOD 发洪
            Out = ofproto_parser.OFPPacketOut(datapath, buffer_id, in_port, actions,arp_resp)  # What is buffer_id???
            datapath.send_msg(Out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def apccept_packet_in(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        pkt_ethernet = pkt.get_protocol(ethernet.ethernet)

        if pkt_ethernet == ether_types.ETH_TYPE_LLDP:
            return
        #获取datapath(虚拟交换机的id), 用dpid初始化一个键值  写进数据库？
        dpid = datapath.id
        self.Mac_Port_Table.setdefault(dpid, {})

        dst = pkt_ethernet.dst
        src = pkt_ethernet.src
        self.Mac_Port_Table[dpid][src] = in_port  # ["src":in_port] 写进数据库？

        # Check whether is it arp packet
        if pkt_ethernet.ether_types == ether_types.ETH_TYPE_ARP:
            a = pkt.get_protocol(arp.arp)
            self.arp_process(datapath, pkt_ethernet, a, in_port)
            return

        # If the packet is not arp packet
        if dst in self.Mac_Port_Table[dpid]:
            out_port = self.Mac_Port_Table[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [ofproto_parser.OFPActionOutput(out_port)]
        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD :
            match = ofproto_parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
