# icomen-mqtt-bridge

This is a drop-in replacement for the icomen cloud, used in some WiFi plugs.
See [HARDWARE.md](HARDWARE.md) for possible supported hardware.

## Connecting

There are 3 ways to connect the plugs to this bridge:
 - a static route in your internet router (tested), either destination based
   or source based
 - static IP configuration of your WiFi plug (tested, works with
   restrictions, see below)
 - DHCP configuration of the DNS for your WiFi plug (not tested, should work)


### Static route (destination based routing)

You need to be able to set static routes in your internet router.

This is tested with a AVM FRITZ!Box, but I think this should work with many
different routers.

 1. Add a static route to 18.185.112.221 with your local server as next hop
 2. Add 18.185.112.221 as an additional IP to your local server
 3. Setup the comen-mqtt-bridge on your server (see below)

_Hint: The IP is taken from the ALDI version of the plug, other hardware may
connect to other hosts._

**Downsides**

- You cannot block internet access of your plug, since it still depends on
  external services out of your control.
  These services are: DNS, NTP
  Most significally it depends on the DNS record of smart2connect.yunext.com
  (in case of the ALDI version),
- You cannot access the IComen cloud from your network anymore.



### Static route (source based routing)

You need to be able to redirect all traffic coming from your plug to your
local server.

 1. Add a static route from all traffic from your plug to your local server as
    next hop
 2. Setup DNS on your server (see below)
 3. Setup the comen-mqtt-bridge on your server (see below)



### Static IP configuration

You can configure the IP settings of the plug statically, includung the DNS
server, but it seems that this setting is ignored. The plug is using the IP
208.67.222.222 (which resolves to dns.opendns.com), not the statically
configured DNS.

Because of that additional steps has to be taken. You need to redirect all
DNS connections from your plug(s) to your local DNS server by adding some
rules to the plugs gateway. This can either be your normal internet router,
or you can configure your local server as gateway for the plug and add some
rules there.

`iptables -t nat -A PREROUTING -p udp -s ${IP_PLUG} --dport 53 -j DNAT --to-destination ${IP_LOCAL_DNS}`



### DHCP

This method is not tested yet, but it should work.

Traffic dumps show that the plug is indeed using the assigned DNS server,
so assigning your local DNS to your plug should be enough.

Optionally you can also assign your local server as gateway.



## Connection sequence

Here are some hints for configuring your DNS (see hostnames in 1. and 3.).
The queried hosts are taken from the ALDI version of the plug, other hardware
may connect to other hosts.


1. DNS queries:
   - time.pool.aliyun.com
   - ntp.sjtu.edu.cn

2. NTP query:
   - first server of first DNS query

3. DNS query [3]:
   - smart2connect.yunext.com
   -> IP 18.185.112.221

4. Connect to [3], Port 7531

5. [3] is propably a load balancing mechanism, answers with IP and port to
   connect next to

6. Connected. No new load balancing on reconnect.





## Configuration


### icomen.py

Currently you need to set your MQTT broker in icomen.py (line 20).
As an alternative you can add "your-mqtt-broker" to /etc/hosts

You can set the listener_first_ip (see icomen.py line 30) to the IP of your
local server in case you want it to listen on only one interface.
Otherwise leave it at 0.0.0.0 to listen on all interfaces.

Make sure your server starts the bridge (./icomen.py) automatically on boot.




### DNS

This method should be preferred, as it also catches some DNS queries made by
the plug.

The plug could then be blocked completely from the internet.

Also, this method would make it possible to connect the bridge to the icomen
cloud and let it act as a proxy.
This is a planned feature which is not implemented yet.

Here's a config snippet for dnsmasq to catch the DNS querys from the plug.
Replace the given IP addresses with your own.

```
# The plug makes queries for 2 different time servers
address=/time.pool.aliyun.com/192.168.1.1
address=/ntp.sjtu.edu.cn/192.168.1.1

# Catch all *.yunext.com queries
# ALDI uses smart2connect.yunext.com
# Other plugs are maybe using other addresses
address=/yunext.com/192.168.1.20
```


### NTP

In case your router doesn't have an internal NTP server you need to setup your
own, if you want to block internet access for your plugs.
Otherwise you could use a public one, for example pool.ntp.org.



## Using

The bridge handles all encryption and decryption of the packet payloads to and
from the plugs. If you use raw commands then it also handles payload padding.

Replace xxxxxxxxxxxx in the examples with your lower case mac address.


### Sending commands through MQTT

The bridge expects commands to be sent to the MQTT topic
`icomen/cmnd/xxxxxxxxxxxx/<COMMAND>`.

At the moment there is only one predefined command (`POWER`), but it is also
possible to send raw commands to `RequestRAW`.


#### Predefined commands

To turn on and off a plug you can use the POWER command with value ON or OFF:

```
mosquitto_pub -h sausier -t 'icomen/cmnd/xxxxxxxxxxxx/POWER' -m "ON"
mosquitto_pub -h sausier -t 'icomen/cmnd/xxxxxxxxxxxx/POWER' -m "OFF"
```

#### Raw commands

For commands see [PROTOCOL.md](PROTOCOL.md).

To turn on and off a plug using raw commands you have to use command 01 with
the corresponding command data:

```
mosquitto_pub -h sausier -t 'icomen/cmnd/xxxxxxxxxxxx/RequestRAW' -m "010000ffff"
mosquitto_pub -h sausier -t 'icomen/cmnd/xxxxxxxxxxxx/RequestRAW' -m "01000000ff"
```

### Receiving switch state through MQTT

The bridge publishes the switch state to the following topic:
```
icomen/stat/xxxxxxxxxxxx/POWER
```


### Debugging

The bridge publishes all packets it sends and receives to the following topics:
```
icomen/raw/xxxxxxxxxxxx/RECV
icomen/raw/xxxxxxxxxxxx/SEND
```
These packets are decrypted, so you can directly see the payload. Also the
packets are grouped by 8 bytes and encoded in hex.

