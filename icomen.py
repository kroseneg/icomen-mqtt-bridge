#!/usr/bin/env python3

import daemon

import select, socket, sys, queue
import re

from binascii import hexlify, unhexlify

from Cryptodome.Cipher import AES
import random
import calendar
import time

from textwrap import wrap

from paho.mqtt import client as mqtt_client

#mqtt_broker = "localhost"
mqtt_broker = "your-mqtt-broker"
mqtt_port = 1883
mqtt_topic_base = "icomen"
mqtt_client_id = f'python-mqtt-{random.randint(0, 1000)}'
mqtt_username = ""
mqtt_password = ""


listener_first_ip   = '18.185.112.221'
listener_first_port = 7531
# The oniginally used second IP is the following, but also use the first one
# for the second listener, for making our life easier.
#listener_second_ip   = '52.24.113.48'
listener_second_ip = listener_first_ip
listener_second_port = 7533
# first_ip = ''


def debug_print(text):
	# Change to True if you want debug output
	if (False):
		print(text)



class AESCipher:
	def __init__(self, key):
		self.key = key.encode()

	def encrypt(self, data):
		iv = self.key[:AES.block_size]
		self.cipher = AES.new(self.key, AES.MODE_CBC, iv)
		return self.cipher.encrypt(data)

	def decrypt(self, raw):
		iv = self.key[:AES.block_size]
		self.cipher = AES.new(key=self.key, mode=AES.MODE_CBC, iv=iv)
		return self.cipher.decrypt(raw)



class IComenPacketHeader():

	prefix = ""
	lock = ""
	mac = ""

	def __init__(self, raw_head):
		self.A_prefix = hexlify(raw_head[0:0+1])
		self.B_lock = hexlify(raw_head[1:1+1])
		self.C_mac_address = hexlify(raw_head[2:2+6])
		lenraw = raw_head[8:8+1]
		self.D_data_length = ord(lenraw)



class IComenPacketPayload():

	data = []
	commandHandler = None

	def __init__(self, raw_data):
		self.A_prefix  = hexlify(raw_data[0:0+1])
		self.B_packet_counter = hexlify(raw_data[1:1+2])
		self.B_packet_counter_n = (int.from_bytes(raw_data[1:1+2], "little"))
		self.B_packet_counter_x = hexlify(self.B_packet_counter_n.to_bytes(2, "little"))
		self.C_company_code = hexlify(raw_data[3:3+1])
		self.D_device_type = hexlify(raw_data[4:4+1])
		self.E_authentication_code = hexlify(raw_data[5:5+2])
		self.F_command = hexlify(raw_data[7:])





class IComenCommandHandler:

	plug = None

	raw_command = None

	def dict(self):
		self.decode_command = {
#			'01': self.switching,
			'02': self.switchState,
#			'03': "Timer Set",
#			'04': "Timer Query",
#			'05': "Timer Delete",
			'06': self.manualSwitching,
#			'09': "Antithief Set",
#			'0A': "Antithief Query",
#			'23': "Search",
			'41': self.switchServer,
			'42': self.encryptionKey,
			'44': self.timestamp,
			'61': self.heartbeat
		}


	def __init__(self, plug, raw_command):
		self.plug = plug

		self.dict()

		self.raw_command = raw_command

		stripped_command = re.sub(r'(08)*$', "", raw_command.decode())

		this_command = stripped_command[:2]
		this_command_data = stripped_command[2:]

		callback = self.decode_command.get(this_command, self.unknown_command)

		debug_print("IComenCommandHandler: CALLBACK: {}({},{})".format(callback.__func__.__qualname__, this_command, this_command_data))


		if callback is not None:
			callback(this_command, this_command_data)


	def unknown_command(self, command, data):
		debug_print("UNKNOWN COMMAND[{}] DATA[{}]".format(command, data))



	# request  0140xxxxxxxxxxxx10 000000c21192dd06 0000ffff04040404
	# response 0140xxxxxxxxxxxx10 000200c21192dd06 000000ff04040404
	def manualSwitching(self, command, data):
		self.switchState(command, data)

	def switchState(self, command, data):
		state = "UNKNOWN"
		if data[4:6] == "ff":
			state = "ON"
		elif data[4:6] == "00":
			state = "OFF"

		self.plug.mqtt_send("stat", "POWER", state, True)




	# request  0140xxxxxxxxxxxx10 000000c21192dd41 0808080808080808
	# response 0142xxxxxxxxxxxx10 000000c21192dd41 12b970dd1d6d0202
	def switchServer(self, command, data):
		debug_print("COMMAND[{}] DATA[{}]".format(command, data))
		if self.plug is not None:

			self.plug.send_data(unhexlify(b""
				+b"41"					# Command
#				+b"34187130"			# IP
#				+b"1d6d"					# Port
				+hexlify(socket.inet_aton(listener_second_ip))			# IP
				+hexlify(listener_second_port.to_bytes(2, "big"))			# Port
			), response=True)



	# request  0140xxxxxxxxxxxx10 000000c21192dd42 0808080808080808
	# response 0142xxxxxxxxxxxx20 000000c21192dd42 106c6b6168363738 74396b7371373036 6d07070707070707
	def encryptionKey(self, command, data):
		if self.plug is not None:
#			new_key = "lkah678t9ksq706m"
			new_key = self.plug.key

			self.plug.send_data(unhexlify(b""
				+b"42"					# Command
				+b"10"					# Bytes of Command data
				+hexlify(new_key.encode())	# Command data
			), response=True)

			self.plug.key = new_key



	def heartbeat(self, command, data):
		# request  0140xxxxxxxxxxxx10 000000c21192dd61 0808080808080808
		# response 0142xxxxxxxxxxxx10 000000c21192dd61 001e060606060606
		if self.plug is not None:
			self.plug.send_data(unhexlify(b""
				+b"61"					# Command
				+b"001e"					# Port
			), response=True)



	# request  0140xxxxxxxxxxxx10 000000c21192dd44 0808080808080808
	# response 0142xxxxxxxxxxxx10 000000c21192dd44 638d241204040404
	def timestamp(self, command, data):
		if self.plug is not None:
			current_GMT = time.gmtime()
			time_stamp = calendar.timegm(current_GMT)

			self.plug.send_data(unhexlify(b""
				+b"44"					# Command
				+"{:x}".format(time_stamp).encode()		# Port
			), response=True)




def mqtt_connect():
	def on_connect(client, userdata, flags, rc):
		if rc == 0:
			debug_print("MQTT: Connected to Broker!")
			client.subscribe('icomen/cmnd/#')
		else:
			debug_print(("MQTT: Failed to connect, return code %d\n", rc))

	def on_disconnect(client, userdata, rc):
		if rc == 0:
			debug_print("MQTT: Disconnected from Broker!")
		else:
			debug_print(("MQTT: Unexpected disconnection, return code %d\n", rc))

	def on_message(client, userdata, message):
		debug_print("MQTT: on_message: [{}] [{}]".format(message.topic, message.payload))

	# Set Connecting Client ID
	client = mqtt_client.Client(mqtt_client_id)
	client.username_pw_set(mqtt_username, mqtt_password)
	client.on_connect = on_connect
	client.on_disconnect = on_disconnect
	client.on_message = on_message

	try:
		client.connect(mqtt_broker, mqtt_port)
	except:
		debug_print("MQTT: Connection failed!")

	return client


def mqtt_publish_msg(msg, topic, retain=False):
	topic = "{}/{}".format(mqtt_topic_base, topic)
	result = client.publish(topic, msg, retain=retain)
	status = result[0]
	if status == 0:
		debug_print(f"MQTT: Sent `{msg}` to topic `{topic}`")
	else:
		debug_print(f"MQTT: Failed to send message to topic {topic}")

def mqtt_callback_add(mac_address, callback):
	debug_print("MQTT: adding callback for {}  [{}]: ".format(mac_address, callback))
	client.message_callback_add('icomen/cmnd/{}/#'.format(mac_address.decode('UTF-8')), callback)

def mqtt_callback_remove(mac_address, callback):
	client.message_callback_remove('icomen/cmnd/{}/#'.format(mac_address))


class IComenPacket:

	completed = False

	raw_head = None
	raw_body = None

	key = None
	head = None
	data = None


class IComenPlug:
	
	key = "0123456789abcdef"
	queue = queue.Queue()
	mac_address = b"ffffffffffff"
	company_code = b'ff'
	device_type = b'ff'
	auth_code = b'ffff'
	packet_counter = 0


	received_data = b""

	master = None
	socket = None

	def __init__(self, master, socket):
		self.master = master
		self.socket = socket


	def dict_mqtt_command_map(self):
		self.mqtt_command_map = {
			'icomen/cmnd/' + self.mac_address.decode('UTF-8') + '/POWER': self.mqtt_cmnd_POWER,
			'icomen/cmnd/' + self.mac_address.decode('UTF-8') + '/RequestRAW': self.mqtt_cmnd_RequestRAW,
			'icomen/cmnd/' + self.mac_address.decode('UTF-8') + '/ResponseRAW': self.mqtt_cmnd_ResponseRAW
		}

	def mqtt_cmnd_POWER(self, message):
		if message.payload == b"ON":
			self.send_data(unhexlify(b""
				+b'010000'
				+b'ffff'
			), response=False)
			
		elif message.payload == b"OFF":
			self.send_data(unhexlify(b""
				+b'010000'
				+b'00ff'
			), response=False)


	def mqtt_cmnd_RequestRAW(self, message):
		self.send_data(unhexlify(message.payload), response=False)

	def mqtt_cmnd_ResponseRAW(self, message):
		self.send_data(unhexlify(message.payload), response=True)


	def verbose_raw_packet(self, is_received, raw_head, raw_body, mac_address):
		hex_head = hexlify(raw_head)
		hex_body = hexlify(raw_body)
		debug_print("- data {} [{}] [{}]".format(("received" if is_received else "sent"), hex_head, hex_body))
		
		mqtt_publish_msg(
			"{} {} {}".format(
				hex_head.decode('utf-8')[0:2],
				hex_head.decode('utf-8')[2:],
				" ".join(wrap(hex_body.decode('utf-8'), 16))
			),
			"raw/" + mac_address.decode('utf-8') + "/" + {False:"SEND", True:"RECV"}[is_received]
		)


	def on_mqtt_message(self, client, userdata, message):
		debug_print("MQTT: IComenPlug.on_message: [{}] [{}]".format(message.topic, message.payload))
		callback = self.mqtt_command_map.get(message.topic, None)
		if callback is not None:
			callback(message)


	def register_device(self, packet):
		if self.mac_address == b"ffffffffffff":
			self.mac_address = packet.head.C_mac_address

			self.company_code = packet.data.C_company_code
			self.device_type = packet.data.D_device_type
			self.auth_code = packet.data.E_authentication_code

			self.dict_mqtt_command_map()
			mqtt_callback_add(self.mac_address, self.on_mqtt_message)

			self.send_data(unhexlify(b"02"), response=False)



	def handlePacket(self, data):
		packet = IComenPacket()

		packet.raw_head = self.received_data[:9]
		packet.head = IComenPacketHeader(packet.raw_head)
		
		end = 9 + packet.head.D_data_length

		if len(data) >= end:
			raw_body_encrypted = self.received_data[9:end]
			packet.raw_body = AESCipher(self.key).decrypt(raw_body_encrypted)

			packet.data = IComenPacketPayload(packet.raw_body)

			self.packet_counter = packet.data.B_packet_counter_n

			debug_print("HEAD[{}]  BODY[{}]".format(hexlify(packet.raw_head), hexlify(packet.raw_body)))

			self.received_data = self.received_data[end:]
			packet.completed = True

			self.register_device(packet)

			return packet

		else:
			debug_print("HEAD[{}]  BODY[{}]".format(hexlify(packet.raw_head), hexlify(packet.raw_body)))
			packet.completed = False
			return packet


	def receive(self):
		try:
			received_data = self.socket.recv(1024)
			
			self.received_data += received_data
		except:
			return False

		try_to_parse_data = True
		while self.received_data and try_to_parse_data:
			debug_print("- data received [{}]".format(hexlify(self.received_data)))

			if self.received_data[:1] == b'\x01':
				debug_print("LEN={}".format(int.from_bytes(self.received_data[8:8+1], "little")))

				packet = self.handlePacket(self.received_data)
				try_to_parse_data = packet.completed

				self.verbose_raw_packet(True, packet.raw_head, packet.raw_body, packet.head.C_mac_address)
				IComenCommandHandler(self, packet.data.F_command)

			else:
				debug_print("Unknown Data")
				return False


		if not received_data:
			debug_print("empty data")
			return False


		return True


	def mqtt_send(self, group: str, topic: str, data: str, retain: bool=False):
		mqtt_publish_msg(
			"{}".format(
				data
			),
			group + "/" + self.mac_address.decode('utf-8') + "/" + topic,
			retain
		)
	



	def send_raw(self, data):
		debug_print("IComenPlug:  SEND to s[{}]...".format(self.socket.getpeername()))
		debug_print("IComenPlug:   -> DATA[{}]".format(hexlify(data)))
		self.master.send(self.socket, data)


	def send(self, head, body):
		body_crypted = AESCipher(self.key).encrypt(body)
		debug_print("IComenPlug:  SEND to s[{}]...".format(self.socket.getpeername()))
		debug_print("IComenPlug:   -> HEAD[{}] BODY[{}]".format(hexlify(head), hexlify(body)))
		debug_print("IComenPlug:   -> HEAD[{}] BODY[{}]".format(hexlify(head), hexlify(body_crypted)))
		self.verbose_raw_packet(False, head, body, b"------------")
		self.master.send(self.socket, head + body_crypted)


	def send_data(self, data, response=True):
		if response:
			mode = b'2'
		else:
			mode = b'0'
			self.packet_counter = self.packet_counter + 1

		if self.packet_counter >= 65536:
			self.packet_counter = 0

		payload = unhexlify(b""
			+b"00"		# Prefix
			+hexlify(self.packet_counter.to_bytes(2, "little"))
			+self.company_code
			+self.device_type
			+self.auth_code
		) + data

		payload = self.pad_payload(payload)

		header = unhexlify(b'01'
			+ b'4'   #  4_ = encrypted(?)
			+ mode   #  _0 = request   _2 = response
			+ self.mac_address
			+ "{:x}".format(len(payload)).encode()
			)
		
		payload_encrypted = AESCipher(self.key).encrypt(payload)
		
		self.verbose_raw_packet(False, header, payload, self.mac_address)
		self.master.send(self.socket, header + payload_encrypted )



	def pad_payload(self, payload: bytes):
		length = len(payload)
		required_pad = (16 - length % 16) % 16
		n = required_pad
		while n > 0:
			payload = payload + chr(required_pad).encode()
			n = n - 1
		return payload



class IComen:

	listener = []
	inputs = []
	outputs = []

	plugs = {}

	key = "0123456789abcdef"

	def run(self):

		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.setblocking(0)
#		self.server.bind(('18.185.112.221', 7531))
		self.server.bind((listener_first_ip, listener_first_port))
		self.server.listen(5)

		self.listener.append(self.server)

		self.server2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server2.setblocking(0)
#		self.server2.bind(('52.24.113.48', 7533))
		self.server2.bind((listener_second_ip, listener_second_port))
		self.server2.listen(5)

		self.listener.append(self.server2)

		while self.listener + self.inputs:
			readable, writable, exceptional = select.select(self.listener + self.inputs, self.outputs, self.listener + self.inputs)
			
			for s in readable:
				if s in self.listener:
					connection, client_address = s.accept()
					debug_print("New connection {} from {}".format(connection, client_address))
					mqtt_publish_msg("New connection: {}".format(client_address), "GATEWAY/connection")
					connection.setblocking(0)
					self.inputs.append(connection)
					self.plugs[connection] = IComenPlug(self, connection)

				else:
					received = self.plugs[s].receive()

					if not received:
						debug_print("Closed connection {} from {}".format(connection, client_address))
						mqtt_publish_msg("Closed connection: {}".format(client_address), "GATEWAY/connection")
						if s in self.outputs:
							debug_print("==> removing from outputs")
							self.outputs.remove(s)
						if s in writable:
							debug_print("==> removing from writable")
							writable.remove(s)
							debug_print("==> removing from inputs")
						self.inputs.remove(s)
						s.close()
						del self.plugs[s]

			for s in writable:
				try:
					next_msg = self.plugs[s].queue.get_nowait()
				except queue.Empty:
					self.outputs.remove(s)
				else:
					debug_print("IComen:  SEND  to s[{}] DATA[{}]".format(s.getpeername(), hexlify(next_msg)))
					s.send(next_msg)

			for s in exceptional:
				self.inputs.remove(s)
				if s in self.outputs:
					self.outputs.remove(s)
				s.close()
				del self.plugs[s]


	def send(self, s, data):
		debug_print("IComen:  QUEUE to s[{}] DATA[{}]".format(s.getpeername(), hexlify(data)))
		s.send(data)


	def disconnect_all(self):
		for s in self.listener:
			debug_print("Closing listener {}".format(s.getsockname()))
			s.close()
			self.listener.remove(s)

		for s in self.inputs:
			debug_print("Closing socket {}".format(s.getpeername()))
			s.close()
			self.inputs.remove(s)


if False:
	with daemon.DaemonContext():
		client = mqtt_connect()
#		client.loop_start()
		client.loop_forever()

		master = IComen()
		master.run()

else:
	client = mqtt_connect()
	client.loop_start()

	master = IComen()

	try:
		master.run()
	except KeyboardInterrupt:
		debug_print("")
		master.disconnect_all()
		debug_print("All work done, have fun! :)")
	else:
		pass

