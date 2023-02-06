# icomen-mqtt-bridge

This is a drop-in replacement for the icomen cloud, used in some WiFi plugs.
See [HARDWARE.md](HARDWARE.md) for possible supported hardware.

## Using

There are 2 ways to use this bridge:
 - a static route in your internet router (tested)
 - manual configuration of the DNS in your WiFi plug (not tested yet, should work)


### Static route method

You need to be able to set static routes in your internet router, and you need to set at least one second IP on your local server.

The IP is taken from the ALDI version of the plug, other hardware may connect to other hosts.

 1. Add 18.185.112.221 as an additional IP to your local server
 2. Add a static route to 18.185.112.221 with your local server as next hop
 3. Set your MQTT broker in icomen.py (or add "your-mqtt-broker" to your /etc/hosts)
 4. Start the bridge (./icomen.py)
 5. Turn on your plug
 6. Enjoy :)


### DNS method

This method is not tested yet, but should be preferred, as it also catches some DNS queries made by the plug.

Also, this method would make it possible to connect the bridge to the icomen cloud and let it act as a proxy.
This is a planned feature which is not implemented yet.


Currently you need to set the listener_first_ip (see icomen.py) to the IP of your local server.

Here are some hints for configuring your DNS (see hostnames in 1. and 3.).
The queried hosts are taken from the ALDI version of the plug, other hardware may connect to other hosts.


1. DNS queries:
   - time.pool.aliyun.com
   - ntp.sjtu.edu.cn

2. NTP query:
   - first server of first DNS query

3. DNS query [3]:
   - smart2connect.yunext.com
   -> IP 18.185.112.221

4. Connect to [3], Port 7531

5. [3] is propably a load balancing mechanism, answers with IP and port to connect next to

6. Connected. No new load balancing on reconnect.

