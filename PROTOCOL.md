# Protocol description

Everything listed here is reverse engineered by me or taken from informations
posted on some websites or forums (see [CREDITS.md](CREDITS.md))


## Packet

```
+---------+---------+---------+---------+---------+---------+---------+---------+
|    1    |    2    |    3    |    4    |    5    |    6    |    7    |    8    |
+---------+---------+---------+---------+---------+---------+---------+---------+
|         |
|  Start  |
|         |
+---------+---------+---------+---------+---------+---------+---------+---------+
|         |                                                           |         |
|  Type   |              M  A  C  -  A  d  d  r  e  s  s              | Length  |
|         |                                                           |         |
+---------+---------+---------+---------+---------+---------+---------+---------+
|                                                                               |
|                       E n c r y p t e d   P a y l o a d                       |
|                                                                               |
+---------+---------+---------+---------+---------+---------+---------+---------+
```

* Start
  - Start of packet, always `0x01`

* Type:
  - 0x4_: Data is encrypted (?)
  - 0x_0: Request (?)
  - 0x_2: Response (?)

* MAC-Address:
  - MAC address of the plug

* Length:
  - Length of the payload, always aligned to 16 bytes

* Encrypted Payload:
  - Payload, encrypted with AES-128-CBC, the initial key is "0123456789abcdef"
    The key can be updated at any time, but it seems to get only updated once
    after the second connection is established



## Payload

The payload is encrypted in the packet, description is for decrypted payload

```
+---------+---------+---------+---------+---------+---------+---------+---------+
|    1    |    2    |    3    |    4    |    5    |    6    |    7    |    8    |
+---------+---------+---------+---------+---------+---------+---------+---------+
|         |                   |         |         |                   |         |
|  0x00   |      Counter      | Company | DevType |     Auth-Code     | Command |
|         |                   |         |         |                   |         |
+---------+---------+---------+---------+---------+---------+---------+---------+
|                                                                               |
|              D  A  T  A      w  i  t  h      p  a  d  d  i  n  g              |
|                                                                               |
+---------+---------+---------+---------+---------+---------+---------+---------+
```


* Start:
  - Start of payload, always 0x00

* Counter:
  - Packet counter gets incremented sometimes, not exactly clear when

* Company:
  - Company code
    - `0xC1`: Lidl Silvercrest SWS A1
    - `0xC2`: Aldi Easy Home WiFi

* DevType:
  - Device type, maybe always 0x11

* Auth-Code
  - Authentication code
    - `0x71 0x50`: Lidl Silvercrest SWS A1
    - `0x92 0xDD`: Aldi Easy Home WiFi

* Command
  - command to execute, see table below

* DATA with padding
  - command data, padded to the next 16 byte boundary
    The padding bytes equals to the padding length
    Examples:
    - 4 bytes padding: 0x04 0x04 0x04 0x04
    - 8 bytes padding: 0x08 0x08 0x08 0x08 0x08 0x08 0x08 0x08


| Command | Type     | Direction | Data lendth | Description       |
| -------:| -------- | --------- | -----------:| ----------------  |
|    0x02 | Request  | to Plug   |     4 Bytes | Set switch state  |
|         | Response | from Plug |     4 Bytes |                   |
|         |          |           |             |                   |
|    0x06 |          | from Plug |     4 Bytes | Switch state info |
|         |          |           |             |                   |
|    0x08 | Request  | to Plug   |     ? Bytes | Set slave state   |
|         | Response | from Plug |     ? Bytes |                   |
|         |          |           |             |                   |
|    0x41 | Request  | from Plug |         --- | Change Server     |
|         | Response | to Plug   |     6 Bytes |                   |
|         |          |           |             |                   |
|    0x42 | Request  | from Plug |         --- | Encryption key    |
|         | Response | to Plug   |    17 Bytes |                   |
|         |          |           |             |                   |
|    0x44 | Request  | from Plug |         --- | Heartbeat         |
|         | Response | to Plug   |     6 Bytes |                   |
|         |          |           |             |                   |
|    0x61 | Request  | from Plug |         --- | Timestamp         |
|         | Response | to Plug   |     4 Bytes |                   |
|         |          |           |             |                   |


