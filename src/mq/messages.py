from enum import Enum


class Message:
	pass


class GPS_Pose(Message):
	lat: int
	long: int


class ZMQTopics(Enum):
	"""Enum for ZMQ topics"""

	DROP_LOAD = 1
	PICK_LOAD = 2
	RAISE_HOOK = 3
	DROP_HOOK = 4
	STATUS = 5
	VIDEO = 6
	PROCESSED_VIDEO = 7


class VincFuncs:
	def drop_load():
		pass

	def pick_load():
		pass

	def vinc_drop(self, _):
		pass
