Learn Ryu  
---
### ryu/ryu下的主要目录   
* app  
app下主要放置的是应用类组件(官方写好的列子，也可以在实际情况下使用)、基于REST API的应用组件  

* base  
base中有一个非常重要的文件：app_manager.py，其作用是RYU应用的管理中心，用于加载RYU应用程序，接受从APP发送过来的信息，同时也完成消息的路由。
其主要的函数有app注册、注销、查找、并定义了RyuApp基类，定义了RyuApp的基本属性。包含name, threads, events, event_handlers和observers等成员，以及对应的许多基本函数。如：start(), stop()等  

* controller  
controller文件夹中许多非常重要的文件，如events.py, ofp_handler.py, controller.py等。其中controller.py中定义了OpenFlowController基类。用于定义OpenFlow的控制器，用于处理交换机和控制器的连接等事件，同时还可以产生事件和路由事件。其事件系统的定义，可以查看events.py和ofp_events.py。
在ofp_handler.py中定义了基本的handler，完成了基本的如：握手，错误信息处理和keep alive 等功能。更多的如packet_in_handler应该在app中定义。
在dpset.py文件中，定义了交换机端的一些消息，如端口状态信息等，用于描述和操作交换机。如添加端口，删除端口等操作。  

* lib  
lib中定义了我们需要使用到的基本的数据结构，如dpid, mac和ip等数据结构。在lib/packet目录下，还定义了许多网络协议，如ICMP, DHCP, MPLS和IGMP等协议内容。而每一个数据包的类中都有parser和serialize两个函数。用于解析和序列化数据包。
lib目录下，还有ovs, netconf目录，对应的目录下有一些定义好的数据类型  

* ofproto  
基本分为两类文件，一类是协议的数据结构定义，另一类是协议解析，也即数据包处理函数文件。如ofproto_v1_0.py是1.0版本的OpenFlow协议数据结构的定义，而ofproto_v1_0_parser.py则定义了1.0版本的协议编码和解码。实现功能与协议相同。  

* topology  
包含了switches.py等文件，基本定义了一套交换机的数据结构。event.py定义了交换上的事件。dumper.py定义了获取网络拓扑的内容。最后api.py向上提供了一套调用topology目录中定义函数的接口。  

* cmd  
ryu的命令系统，例如：ryu-manager ×××××.py  

* contrib  

* services  
完成了BGP和vrrp的实现  

* tests  
单元测试 
---  
### Ryu用法  
* app_manager
    ```python
    from ryu.base import app_manager
    ....
    class L2Switch(app_manager.RyuApp):
        def __init__(self, *args, **kwargs):
            super(L2Switch, self).__init__(*args, **kwargs)
        #......
    ```
    继承app_manager.RyuApp基类，其中定义了Ryu的App基本的属性，类定义在ryu/ryu/base/app_manager.py  

* set_ev_cls 装饰器  
    + 当Ryu收到OpenFlow packet_in消息时，将调用此方法  
    + 第一个参数指示应调用此函数的事件类型
    + 第二个参数指示开关的状态(有四种，该类定义在ryu/controller/handler):  
        + HANDSHAKE_DISPATCHER  
            发送和等待握手包  
        + CONFIG_DISPATCHER     
            协商版本并发送功能请求消息  
        + MAIN_DISPATCHER  
            交换功能消息已接收并已发送set-config消息  
        + DEAD_DISPATCHER  
            与对等方断开连接，或者由于一些不可恢复的错误而断开连接。  
    ```python
    .....
    class L2Switch(app_manager.RyuApp):
        OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    
        def __init__(self, *args, **kwargs):
            super(L2Switch, self).__init__(*args, **kwargs)
    
        @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
        def packet_in_handler(self, ev):
            msg = ev.msg         #ev.msg：每一个事件类ev中都有msg成员，用于携带触发事件的数据包。
            dp = msg.datapath    #msg.datapath：已经格式化的msg其实就是一个packet_in报文，msg.datapath直接可以获得packet_in报文的datapath结构。datapath用于描述一个交换网桥。也是和控制器通信的实体单元。datapath.send_msg()函数用于发送数据到指定datapath。通过datapath.id可获得dpid数据
            ofp = dp.ofproto     #datapath.ofproto对象是一个OpenFlow协议数据结构的对象，成员包含OpenFlow协议的数据结构，如动作类型OFPP_FLOOD。
            ofp_parser = dp.ofproto_parser  #datapath.ofp_parser则是一个按照OpenFlow解析的数据结构
    
            actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)] #actions是一个列表，用于存放action list，可在其中添加动作,通过ofp_parser类，可以构造构造packet_out数据结构。括弧中填写对应字段的赋值即可
            out = ofp_parser.OFPPacketOut(
                datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
                actions=actions)  
            dp.send_msg(out)
    ```
* 运行  
```
    ryu-manager ×××××.py
```

  
### REST API   
* 该REST_API类定义在ryu/app下(ofctl_rest.py)
* 如何你没有了解过mininet,请移步到编写的[mininet简单文档](),可以帮你快速了解
* 使用  
  （一）开启Ryu控制器
    ```
        ryu-manager ofctl_rest.py ×××××.py --observer-links --verbose       #observer开启监控，verbose输出信息 
    ```  
   (二) 开启mininet
    ```
        mn --topo=tree, depth=2, fanout=3   #tree表示是树形的网络拓扑，depth表示交换机有多少层，fanout表示所有的交换机作为父节点，有多少个子树。
    ```
   (三)发送URL请求，参考[Ryu官方文档](https://ryu.readthedocs.io/en/latest/app/ofctl_rest.html),里面包含了REST API的所有请求路径、请求内容和相应参数 
    
