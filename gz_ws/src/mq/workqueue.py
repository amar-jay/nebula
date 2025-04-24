import messages
import zmq
import json

class Socket:

	def __init__(self, address, is_sender=False):
		self.context = zmq.Context()
		self.address = address
		self.is_sender = is_sender
		self.socket = self.context.socket(zmq.PUSH if is_sender else zmq.PULL)
		self.socket.connect(address)


	def sender(self):
		self.result_sender = self.context.connect(self.address)

	def send_message(self, message: messages.Message):
		if not self.is_sender:
			raise Exception("receiver cannot send messasges")

		message_str = # json decode message
		self.socket.send(message_str)
		pass
	
	def receive_message(self, message_type: messages.Message, timeout=None):
		message = self.socket.recv()
		json.load()
