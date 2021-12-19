import os
import json
import requests
import random
import hashlib
import time

# Current version
VERSION = 2

def upload_cake(path, slice_size):
	"""
	Takes in a file path, and the size of the slices.
	Cuts the file into slices and uploads them one by
	one to discord.
	:param path:
	:param slice_size:
	"""
	# Convert backslashes to slashes, then converts the path to filename
	filename = path.replace('\\', '/').split('/')[-1]
	# Gets the extension of the file and save it as a seperate variable
	file_format = filename.split('.')[-1]
	# Remove the extension from the filename afterwards
	filename = filename.replace('.'+filename.split('.')[-1], '')
	# Create the dictionary that stores the recipe file
	recipe_json = {
		"version": VERSION,
		"filename": filename,
		"format": file_format,
		"timestamp": 0,
		"cake_size": 0,
		"slices": [],
		"checksum_method": "sha256",
		"checksum": ''
	}
	# Print file and upload info
	print("Slice Size:",slice_size)
	print("File:",path)
	# Get file size and store it as a variable
	size = os.path.getsize(path)
	# Also write the file size to the recipe file
	recipe_json["cake_size"] = size//slice_size+1
	print("File Size:",size)

	# The header that our requests will use
	header = {
		"authorization": token,
		"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"
	}

	# Start timing the uploader
	cake_cut_start = time.time()
	# Open the specified file path
	with open(path, 'rb') as f:
		# Get the sha256 hash of the file
		print("Generate checksum hash...")
		recipe_json["checksum"] = hashlib.sha256(f.read()).hexdigest()
		# Generate api url to send requests to from the channel ID
		channel_url = f'https://discord.com/api/v9/channels/{channel_id}/messages'
		# Start creating slices, slice amount is size // slice size + 1
		for index in range(size//slice_size+1):
			# Start timing slice upload
			slice_time_start = time.time()
			# Read file at current position from iterator
			f.seek(index*slice_size)
			# Error retrying while loop
			while True:
				try:
					print(f"Uploading slice {index}...")
					# Data of the request
					data = {
						"payload_json": {
							"content": index,
							"nonce": random.randint(10 ** 18, 10 ** 19 - 1),
							"tts": False
						}
					}
					# Send the request, contains the file and its name, json data and headers
					response = requests.post(url=channel_url, headers=header, data=data,
											 files={f"{index}.slice": f.read(slice_size)})

					# If the response is successful
					if response.status_code == 200:
						# Print info and escape break error retrying while loop
						print(f"Uploaded slice {index}... ({round(time.time()-slice_time_start), 2} s)")
						break
					else:
						# Other wise throw error
						raise Exception("Invalid response code!")
				# If there is an error uploading
				except Exception as e:
					# Print error information
					print(f"Upload error: {e} At slice index {index}: {response.text}")
					# Wait 10 seconds
					print("Waiting 10 seconds...")
					time.sleep(10)
			# On successful slice upload we append its information to the slice list
			recipe_json["slices"].append({
				# We append the slices index for building
				"index": index,
				# We grab the message url from the request response and append it
				"url": response.json()["attachments"][0]["url"]
			})
	# Finished slices upload, get time taken
	cake_cut_end = time.time()-cake_cut_start
	recipe_json["timestamp"] = int(time.time())
	# Print success message
	print(f"Uploaded slices in {round(cake_cut_end, 2)} seconds!")
	# Save recipe JSON
	print("Writing recipe file...")
	with open(f"{filename}.recipe", "w") as json_file:
		json_file.write(json.dumps(recipe_json))


def build_cake(recipe_path):
	"""
	Takes in a recipe path, downloads all of its slices
	and builds a file, then performs a checksum to ensure
	integrity.
	:param recipe_path:
	"""
	# Start timing build
	build_cake_start = time.time()
	# Open recipe file and extract JSON
	print(f"Reading recipe file {recipe_path}...")
	with open(recipe_path, 'r') as recipe_file:
		recipe = json.loads(recipe_file.read())

	# Save JSON info to variables
	filename = recipe["filename"]
	format = recipe["format"]
	slices = recipe["slices"]
	slice_count = recipe['cake_size']
	# Print info and create the empty file
	print(f"Baking cake {filename}.{format} from {slice_count} slices.")
	with open(f'{filename}.{format}', 'wb') as cake:
		# Iterate over the JSON files slices
		for slice in slices:
			# Get the url
			url = slice["url"]
			# Request the url, download its contents and add it to the file
			cake.write(requests.get(url).content)
			# Print info
			print(f"Downloaded slice {slice['index']} out of {slice_count}")
		# Success message
		print(f"Baked cake {filename}!")

	# SHA256 integrity check
	print(f"Performing checksum...")
	with open(f'{filename}.{format}', 'rb') as cake:
		# If our hash isn't the recipes hash
		if hashlib.sha256(cake.read()).hexdigest() != recipe["checksum"]:
			# End build time, we are finished regardless of the failure
			build_cake_end = time.time() - build_cake_start
			# Print error
			print(f"Checksum error! {recipe['checksum_method']} hash does not match!")
			print(f"Cake verification unsuccessful, took {round(build_cake_end, 2)} seconds.")
		# If our hashes do match
		else:
			# End the build time, we are successful
			build_cake_end = time.time() - build_cake_start
			# Print success message
			print(f"Hashes match! Cake successfully baked from recipe! Took {round(build_cake_end, 2)} seconds.")


# Main method, CLI usage
if __name__ == '__main__':
	from sys import argv, exit
	# Mode, either upload or download, used to determine wether use has specified a mode.
	mode = None
	# Default config file location
	config_file = 'config.txt'
	# Default file path (none) for uploading, determines wether the argument is left blank.
	file_path = None

	# Help message
	def show_help():
		print("""
	If you are uploading a file, use -f FILE_PATH to specify a file.
	If you are downloading a file, use -r RECIPE_PATH to specify a recipe.
	Either use case lets you appened -c CONFIG_PATH to optionally specify the config files location.
	Please edit the 'token' field in the config file to a Discord users token for uploading and downloading.
	Edit the 'channel' field to a Discord channel id just for uploading""")
		input("Press any key to continue")
		sys.exit()

	# Welcome message
	print("Welcome to Discord File Storage v2!")

	# If we dont specify any arguments
	if len(argv) == 1:
		show_help()

	# Enumerate over arguments
	for index, arg in enumerate(argv):
		# File specified, upload mode
		if arg == '-f':
			file_path = argv[index + 1].replace('\\', '/')
			mode = "upload"
		# Recipe specified, download mode
		elif arg == '-r':
			recipe_path = argv[index + 1].replace('\\', '/')
			mode = "download"
		# Config file location
		elif arg == '-c':
			config_file = argv[index + 1]
		# Help command
		elif arg in ['-h', '--help']:
			show_help()

	# Input validation, missing fields etc
	if mode == "upload" and file_path is None:
		print("ERROR: NO FILE PATH SPECIFIED")
		show_help()
	if mode == "download" and recipe_path is None:
		print("ERROR: NO RECIPE PATH SPECIFIED")
		show_help()


	# Load config file
	with open(config_file, 'r') as f:
		config_json = json.loads(f.read())
		token = config_json["token"]
		channel_id = config_json["channel"]

	# Upload a file
	if mode == "upload":
		# Run upload cake function, slice size is 8MB
		upload_cake(path=file_path, slice_size=8*10**6)
	# Download a file
	elif mode == "download":
		# Run download function
		build_cake(recipe_path=recipe_path)
	else:
		# No mode selected, show error
		print("ERROR: NO MODE SPECIFIED")
		show_help()


