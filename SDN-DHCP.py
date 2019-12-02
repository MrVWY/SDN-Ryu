from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import packet, ether_types, ethernet, dhcp, ipv4, udp

# DHCP
# ofproto 在这个目录下，基本分为两类文件，一类是协议的数据结构定义，另一类是协议解析，也即数据包处理函数文件。

"""
DHCP的OPTION字段:
    每个Option都由Tag、Len、Data三大部分组成：
        1、Tag表示本Option的作用，1个字节，由RFC2132定义。
        2、Len表明后续Data的长度，1 个字节，（Tag=0、255的比较特殊，没有Len和Data）
        3、Data内容作为Tag的补充详细说明 
"""


class swich(app_manager):

    def __init__(self, *args, **kwargs):
        super(swich, self).__init__(*args, **kwargs)
        self.DHCP_MAC = "",
        self.DHCP_server = "",


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        ofproto_parser = datapath.ofproto_parser
        match = ofproto_parser.OFPMatch()

        action = [ofproto_parser.OFPActionOutput(port=ofproto.OFPP_CONTROLLER,
                                                 max_len=ofproto.OFPCML_NO_BUFFER)]  # (port,max)
        ins = [ofproto_parser.OFPInstructionActions(
            type=ofproto.OFPIT_APPLY_ACTIONS,
            actions=action
        )]
        Out = ofproto_parser.OFPFlowMod(datapath=datapath, priority=0, match=match, instructions=ins)
        datapath.send_msg(Out)

    def get_dhcp_state(self, pkt_dhcp):
        """
        tag:53 ,
        DHCP Message Type:
            1：DHCPDISCOVER 
            2：DHCPOFFER 
            3：DHCPREQUEST 
            4：DHCPDECLINE 
            5：DHCPACK 
            6：DHCPNAK 
            7：DHCPRELEASE

        :param pkt_dhcp:
        :return:
        """

        # for opt in pkt_dhcp.option.option_list:
        #     if opt.tag == 53:
        #         return ord(opt[0].value)
        dhcp_state = ord([opt for opt in pkt_dhcp.options.option_list if opt.tag == 53][0].value)
        if dhcp_state == 1:
            state = 'DHCPDISCOVER'
        elif dhcp_state == 3:
            state = 'DHCPREQUEST'
        return state

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        pkt_ethernet = pkt.get_protocol(dhcp.dhcp)

        if pkt_ethernet:
            self.DHCP_handler(datapath, in_port, pkt)
        return

    def DHCP_handler(self, datapath, port, pkt):
        pkt_dhcp = pkt.get_protocol(dhcp.dhcp)
        dhcp_state = self.get_dhcp_state(pkt_dhcp)
        if dhcp_state == 'DHCPDISCOVER':  #dhcpDiscover
            """
            动态主机配置协议(DHCP)是目前广泛使用的动态IP地址分配方法。
            DHCP客户端启动时，由于其还未配置IP地址，因此只能使用广播方式发送Dhcpdiscover包，即该数据包的源地址为0.0.0.0，目标地址为255.255.255.255。
            """
            self.send_flow_mod(datapath, port, self.assemble_offer(pkt))
        elif dhcp_state == 'DHCPREQUEST': #dhcpRequest
            self.send_flow_mod()

    def send_flow_mod(self, datapath, port, pkt):
        ofproto = datapath.ofproto
        ofproto_parse = datapath.ofproto_parser
        actions = [ofproto_parse.OFPActionOutput(port=port)]
        inst = [ofproto_parse.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        pkt.serialize() #初始化
        Out = ofproto_parse.OFPFlowMod(
            buffer_id=ofproto.OFPCML_NO_BUFFER,
            instructions=inst,
            in_port= ofproto.OFPP_CONTROLLER,
            data=pkt.data
        )
        datapath.send_msg(Out)

    def assemble_offer(self, pkt):
        disc_eth = pkt.get_protocol(ethernet.ethernet)
        disc_ipv4 = pkt.get_protocol(ipv4.ipv4)
        disc_udp = pkt.get_protocol(udp.udp)
        disc = pkt.get_protocol(dhcp.dhcp)
        #remove pkt.dhcp.option.option_list , tag = 55 (Parameter Request List)
        disc.options.option_list.remove(
            next(opt for opt in disc.options.option_list if opt.tag == 55))
        #remove pkt.dhcp.option.option_list , tag = 53 (DHCP Message Type)
        disc.options.option_list.remove(
            next(opt for opt in disc.options.option_list if opt.tag == 53))
        # remove pkt.dhcp.option.option_list , tag = 12 (Host Name)
        disc.options.option_list.remove(
            next(opt for opt in disc.options.option_list if opt.tag == 12))
        #insert pkt.dhcp.option.option_list , tag = 1 (Subnet Mask)
        disc.options.option_list.insert(
            0, dhcp.option(tag=1, value=self.bin_netmask))
        # insert pkt.dhcp.option.option_list , tag = 3 (Router)
        disc.options.option_list.insert(
            0, dhcp.option(tag=3, value=self.bin_server))
        # insert pkt.dhcp.option.option_list , tag = 6 (Domain Name Server 域名服务器)
        disc.options.option_list.insert(
            0, dhcp.option(tag=6, value=self.bin_dns))
        # insert pkt.dhcp.option.option_list , tag = 12 (Host Name)
        disc.options.option_list.insert(
            0, dhcp.option(tag=12, value=self.hostname))
        # insert pkt.dhcp.option.option_list , tag = 53 (DHCP Message Type)
        disc.options.option_list.insert(
            0, dhcp.option(tag=53, value='02'.decode('hex')))
        # insert pkt.dhcp.option.option_list , tag = 54 (Server Identifier)
        disc.options.option_list.insert(
            0, dhcp.option(tag=54, value=self.bin_server))


        #Constructing a Packet
        offer_pkt = packet.Packet()
        #Packet protocol level one
        offer_pkt.add_protocol(ethernet.ethernet(
            ethertype=disc_eth.ethertype, dst=disc_eth.src, src=self.DHCP_MAC))
        #Packet protocol level two
        offer_pkt.add_protocol(
            ipv4.ipv4(dst=disc_ipv4.dst, src=self.DHCP_server, proto=disc_ipv4.proto))
        #Packet protocol level three
        offer_pkt.add_protocol(udp.udp(src_port=67, dst_port=68))
        #Packet protocol level four
        offer_pkt.add_protocol(dhcp.dhcp(op=2,
                                         chaddr=disc_eth.src,
                                         siaddr=self.DHCP_server,
                                         boot_file=disc.boot_file,
                                         yiaddr=self.ip_addr,
                                         xid=disc.xid,
                                         options=disc.options))
        return offer_pkt