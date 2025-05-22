import os


def get_asset(path: str) -> str:
	"""Get the asset path"""
	basePath = "/home/amarjay/Desktop/code/matek/src/new_control_station/assets"
	return os.path.join(basePath, path)
