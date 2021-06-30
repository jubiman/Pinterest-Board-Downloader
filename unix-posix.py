import os
import json
import datetime
import time
import sys
import getopt
from configparser import ConfigParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from distutils.util import strtobool
from random import randint

from getch import getch

import requests
from lxml import html
from tkinter import filedialog

threads = {
	"imgprops": [],
	"download": []
}
images = []
options = ConfigParser()
debug = force = verbose = False
cls = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')


class ImageData:
	def __init__(self, url, name, ext):
		self.url = url
		self.name = name
		self.ext = ext


def configDefaults():
	options['FILENAMES']['customFileNames'] = 'True'
	options['FILENAMES']['customFileName'] = '@created_at'
	options['FILENAMES']['emptyFileName'] = ""
	options['MULTITHREADING']['mx_wrks'] = '0'
	options['FOLDERS']['saves'] = "./downloads"
	options['DUPLICATES']['checkforduplicates'] = "True"
	options['DUPLICATES']['savepinid'] = "True"

	saveConfig()


def loadConfig():
	options.read('config.ini')


def saveConfig():
	with open('config.ini', 'w') as f:
		options.write(f, False)
		f.close()


def parseName(js):
	# TODO: add more options
	name = ""

	# tokenise the string
	currentToken: str = ""
	jsonAttribute = False

	for i, it in enumerate(options["customFileName"]):
		# @ indicates an option (in JSON object) from response > data > @attribute
		if it == "@":
			jsonAttribute = True
		else:
			currentToken += it

	if jsonAttribute:
		date = js[currentToken]
		t = list(date[5:25])
		t[2] = t[6] = '-'
		a = "".join(t[0:11]).split('-')
		month = datetime.datetime.strptime(a[1], "%b").month
		if month < 10:
			month = '0' + str(month)
		a[1] = month
		a = a[::-1]
		a = ['-' + b for b in a]
		name += "".join(list(a[0][1:]) + a[1:] + t[11:])
	return name


def dateConversion(date):
	name = ""
	t = list(date[5:25])
	t[2] = t[6] = '-'
	a = "".join(t[0:11]).split('-')
	month = datetime.datetime.strptime(a[1], "%b").month
	if month < 10:
		month = '0' + str(month)
	a[1] = str(month)
	a = a[::-1]
	a = ['-' + b for b in a]
	name += "".join(list(a[0][1:]) + a[1:] + t[11:])
	return name


def save(file, name, ext):
	if os.path.isfile(options['FOLDERS']['saves'] + '/' + name + ext) and not force:
		print(f'Do you want to overwrite {name + ext}? y/n\t')
		while 1:
			k = getch()
			if k in ['n', 'N']:
				return
			elif k in ['y', 'Y']:
				break
	with open(options['FOLDERS']['saves'] + '/' + name + ext, 'wb') as f:
		f.write(file)
		f.close()


def downloadImg(url, name, ext):
	# TODO: add options
	img = requests.get(url).content
	save(img, name, ext)


def getImgPropsSpecial(pin):
	print(f"WEIRD TYPE ALERT!!! {pin['type']}")
	if debug or True:
		with open("json_logs.json", "a") as f:
			f.write(json.dumps(pin, indent=4))
			f.write("\n\n")
			f.close()
	if pin["type"] == "story":
		for obj in pin["objects"][1:]:
			pin_page = requests.get(f"https://pinterest.com/pin/{obj['id']}")

			script = html.fromstring(pin_page.content).xpath('//script[@id="initial-state"]')
			js = json.loads(script[0].text)
			if debug:
				with open("a.json", "w") as f:
					f.write(json.dumps(js, indent=4, sort_keys=False))
					f.close()

			img_url = ""
			if ('videos' in js["resourceResponses"][0]["response"]["data"]) and \
				js["resourceResponses"][0]["response"]["data"]['videos']:
				v_d = js["resourceResponses"][0]["response"]["data"]['videos']['video_list']
				vDimens = []
				vDimensD = {}
				for v_format, v_v in v_d.items():
					if 'url' in v_v and v_v['url'].endswith('mp4'):
						vDimens.append(v_v['width'])
						vDimensD[v_v['width']] = v_v['url']
				if vDimens:
					vDimens.sort(key=int)
					img_url = vDimensD[int(vDimens[-1])]
			else:
				img_url = pin["images"]["orig"]["url"]
			try:
				name = dateConversion(js["resourceResponses"][0]["response"]["data"]["created_at"])
			except:
				try:
					name = js["resourceResponses"][0]["response"]["data"]["id"]
				except:
					if options["FILENAMES"]["emptyfilename"] != "":
						name = options["FILENAMES"]["emptyfilename"]
					else:
						name = str(randint(0, 1024))
			ext = img_url[img_url.rfind('.'):]
			# We do not want empty file names
			if not name or name == "":
				name = options["customFileName"]
			name = name.replace(':', '-')

			return img_url, name, ext


def getImgProps(pin):
	if debug:
		with open("json_logs.json", "a") as f:
			f.write(json.dumps(pin, indent=4))
			f.write("\n\n")
			f.close()

	if pin['type'] != 'pin':
		return getImgPropsSpecial(pin)

	pin_page = requests.get(f"https://pinterest.com/pin/{pin['id']}")

	script = html.fromstring(pin_page.content).xpath('//script[@id="initial-state"]')
	js = json.loads(script[0].text)
	if debug:
		with open("a.json", "w") as f:
			f.write(json.dumps(js, indent=4, sort_keys=False))
			f.close()

	img_url = ""
	if ('videos' in js["resourceResponses"][0]["response"]["data"]) and \
		js["resourceResponses"][0]["response"]["data"]['videos']:
		v_d = js["resourceResponses"][0]["response"]["data"]['videos']['video_list']
		vDimens = []
		vDimensD = {}
		for v_format, v_v in v_d.items():
			if 'url' in v_v and v_v['url'].endswith('mp4'):
				vDimens.append(v_v['width'])
				vDimensD[v_v['width']] = v_v['url']
		if vDimens:
			vDimens.sort(key=int)
			img_url = vDimensD[int(vDimens[-1])]
	else:
		img_url = pin["images"]["orig"]["url"]
	try:
		name = dateConversion(js["resourceResponses"][0]["response"]["data"]["created_at"])  # ????? not works on 1 fsr
	except:
		try:
			name = js["resourceResponses"][0]["response"]["data"]["id"]
			name = js["resourceResponses"][0]["response"]["data"]["id"]
		except:
			name = str(randint(0, 1024))
	ext = img_url[img_url.rfind('.'):]
	# print(img_url, name + ext)
	# We do not want empty file names
	if not name or name == "":
		name = options["customFileName"]
	name = name.replace(':', '-')

	return img_url, name, ext


def request(board):
	if 'pinterest.com' in board:
		if 'https://' in board:
			source_url = board[board.find('/', 10):]
		else:
			source_url = board[board.find('/'):]
	else:
		source_url = board

	print("Fetching images...")
	start = time.time()

	# Get board ID
	try:
		page = requests.get(f"https://pinterest.com{source_url}")
		script = html.fromstring(page.content).xpath('//script[@id="initial-state"]')
		js = json.loads(script[0].text)
		board_id = js["resourceResponses"][0]["response"]["data"]["id"]
		timestamp = int(time.time() * 1000)
	except:
		print("Failed to get board information. Exitting.")
		return

	url = 'https://pinterest.com/resource/BoardFeedResource/get/'
	bookmark = js["resourceResponses"][1]["options"]["bookmarks"][0]

	pins = js["resourceResponses"][1]["response"]["data"][1:]
	s = requests.Session()
	s.headers = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.0.0 Safari/537.36',
		'Accept': 'application/json, text/javascript, */*, q=0.01',
		'Accept-Language': 'en-US,en;q=0.5',
		'Referer': 'https://www.pinterest.com/',
		'X-Requested-With': 'XMLHttpRequest',
		'X-APP-VERSION': 'b0e3c4c',
		'X-Pinterest-AppState': 'active',
		'DNT': '1',
		'Connection': 'keep-alive',
		'Pragma': 'no-cache',
		'Cache-Control': 'no-cache',
		'TE': 'Trailers'
	}

	while bookmark != '-end-':
		# TODO: add section support
		"""
		if section:
			opts = {
			'isPrefetch': 'false',
			'field_set_key': 'react_grid_pin',
			'is_own_profile_pins': 'false',
			'page_size': 25,
			'redux_normalize_feed': 'true',
			'section_id': section_id,
			}
		"""
		data_options = {
			"isPrefetch": False,
			"board_id": board_id,
			"board_url": source_url,
			"field_set_key": "react_grid_pin",
			"filter_section_pins": True,
			"sort": "default",
			"layout": "default",
			"page_size": 250,
			"redux_normalize_feed": True
		}
		if bookmark:
			data_options.update({"bookmarks": [bookmark]})

		params: dict = {
			"source_url": source_url,
			"data": json.dumps({"options": data_options, "context": {}}),
			"_": timestamp
		}
		try:
			p = s.get(url, params=params)
		except requests.exceptions.RequestException as ex:
			print(ex.with_traceback())
			return

		# DEBUG
		if debug:
			with open("d.json", "w") as f:
				f.write(json.dumps(p.json(), indent=4, sort_keys=False))
				f.close()

		# Extend list of pins
		pins.extend(p.json()["resource_response"]["data"])

		# Set new bookmark
		bookmark = p.json()['resource']['options']['bookmarks'][0]

	end = time.time()
	print(f"Fetched {len(pins)} images. Took {datetime.timedelta(seconds=end-start)}")

	print(f"Generating {len(pins)} images...")
	start = time.time()

	max_workers = None if int(options['MULTITHREADING']['mx_wrks']) == 0 else int(options['MULTITHREADING']['mx_wrks'])

	# Multi-threading
	with ThreadPoolExecutor(max_workers=max_workers) as ex:
		# Go through each pin
		for pin in pins:
			if pin is None:
				continue

			if debug:
				with open("json_logs2.json", "a") as f:
					f.write(json.dumps(pin, indent=4))
					f.write("\n\n")
					f.close()

			if strtobool(options["DUPLICATES"]["checkforduplicates"]):
				with open(os.path.join(options["FOLDERS"]["saves"], "pinids.txt"), "r") as f:
					if pin["id"] in f.read():
						if verbose or debug:
							print(f"Skipping duplicate {pin['id']}")
						continue

			if strtobool(options["DUPLICATES"]["savepinid"]):
				with open(os.path.join(options["FOLDERS"]["saves"], "pinids.txt"), "w+") as f:
					if pin["id"] not in f.read():
						f.write(pin["id"])
						f.write("\n")
						f.close()

			threads["imgprops"].append(ex.submit(getImgProps, pin))

		for task in as_completed(threads["imgprops"]):
			# If the function returned successfully we can download the image
			if isinstance(task.result(), tuple):
				if debug:
					print(task.result()[0], task.result()[1] + task.result()[2])
				images.append(ImageData(*task.result()))
				continue
			# The function failed to execute
			print(task.result())
	end = time.time()
	print(f"Finished generating {len(pins)} images. Took {datetime.timedelta(seconds=end-start)}")

	print(f"Downloading {len(images)} images...")
	start = time.time()

	# Multi-threading
	with ThreadPoolExecutor(max_workers=max_workers) as ex:

		for image in images:
			threads["download"].append(ex.submit(downloadImg, image.url, image.name, image.ext))

		for task in as_completed(threads["download"]):
			# Nothing to do here yet; no return value
			continue
	end = time.time()
	print(f"Finished downloading {len(images)} images. Took {datetime.timedelta(seconds=end-start)}")


def showSettings():
	print("Pinterest Board Downloader Settings\n")
	print("\t1. Filenames")
	print("\t2. Multi-threading")
	print("\t3. Folders")
	print("\t4. Duplicates")
	print("\t5. Load defaults")
	print("\nCopyright (C) Jubiman 2021. All rights reserved. https://github.com/Jubiman/Pinterest-Board-Downloader/")
	print("\t\nESC. Return to console")

	k = getch()
	if k == "1":
		return showFilenames()
	elif k == "2":
		return showMultithreading()
	elif k == "3":
		return showFolders()
	elif k == "4":
		return showDuplicates()
	elif k == "5":
		print("Are you sure you want to reset to defaults? y/n")
		k = getch()
		if k in ['y', 'Y']:
			configDefaults()
	elif k == "\x08" or k == "\x1b":
		cls()
		return saveConfig()
	return showSettings()


def showFilenames():
	while True:
		cls()
		print("Pinterest Board Downloader Settings\n")
		print(f"\t1. Custom file names\033[40G| [{options['FILENAMES']['customFileNames']}]")
		print(f"\t2. Custom file name\033[40G| [{options['FILENAMES']['customFileName']}]")
		print("\tESC. Back to main menu")
		k = getch()
		if k == "1":
			options['FILENAMES']['customFileNames'] = str(not strtobool(options['FILENAMES']['customFileNames']))
		elif k == "2":
			val = input("New value:  ")
			options['FILENAMES']['customFileName'] = val
		elif k == "\x08" or k == "\x1b":
			cls()
			return showSettings()
		return showFilenames()


def showMultithreading():
	while True:
		cls()
		print("Pinterest Board Downloader Settings\n")
		print(f"\t1. Max workers (threads)\033[40G| [{options['MULTITHREADING']['mx_wrks']}]")
		print("\tESC. Back to main menu")
		k = getch()
		if k == "1":
			val = input("New value:  ")
			options['MULTITHREADING']['mx_wrks'] = val
		elif k == "\x08" or k == "\x1b":
			cls()
			return showSettings()
		return showMultithreading()


def showFolders():
	while True:
		cls()
		print("Pinterest Board Downloader Settings\n")
		print(f"\t1. Download folder\033[40G| [{options['FOLDERS']['saves']}]")
		print("\tESC. Back to main menu")
		k = getch()
		if k == "1":
			options['FOLDERS']['saves'] = filedialog.askdirectory(title="Select a local folder where you want to put "
																		"all the pinned pictures")
		elif k == "\x08" or k == "\x1b":
			cls()
			return showSettings()
		return showFolders()


def showDuplicates():
	while True:
		cls()
		print("Pinterest Board Downloader Settings\n")
		print(f"\t1. Check for duplicates\033[40G| [{options['DUPLICATES']['checkforduplicates']}]")
		print(f"\t2. Save pin ID\033[40G| [{options['DUPLICATES']['savepinid']}]")
		print("\tESC. Back to main menu")
		k = getch()
		if k == "1":
			options['DUPLICATES']['checkforduplicates'] = str(not strtobool(options['DUPLICATES']['checkforduplicates']))
		if k == "2":
			options['DUPLICATES']['savepinid'] = str(not strtobool(options['DUPLICATES']['savepinid']))
		elif k == "\x08" or k == "\x1b":
			cls()
			return showSettings()
		return showDuplicates()


def run():
	global debug
	global force
	global verbose
	while True:
		inp = input("$>")
		# inp = "dl https://pinterest.com/humanAF/art-n-stuff/ -f"  # DEBUG
		if inp.lower() == "settings":
			showSettings()
		if inp.lower() == "quit" or inp.lower() == "exit":
			sys.exit(0)
		s = inp.split()
		if s[0] in ["download", 'dl']:
			url = s[1]
			try:
				opts, args = getopt.getopt(s[2:], 'dfv', ["debug=", "force", "verbose"])
			except getopt.GetoptError as err:
				print(err)
				continue
			for o, a in opts:
				if o == '--force':
					force = a
				elif o == '-f':
					force = True
					print('yes')
				if o == '--debug':
					debug = a
				elif o == '-d':
					debug = True
				if o == '--verbose':
					verbose = a
				elif o == '-v':
					verbose = True

			# TODO: add more stuff?
			print(f"Starting operation: downloading board from {url}.\n\tArguments:\n\t\t-f FORCE {force}\n\t\t-d DEBUG {debug}"
					f"\n\t\t-v VERBOSE {verbose}\n\tOptions:\n\t\tCheck for duplicates:\t{options['DUPLICATES']['checkforduplicates']}"
					f"\n\t\tDownload folder:\t{options['FOLDERS']['saves']}\n\t\tMax threads:\t\t{options['MULTITHREADING']['mx_wrks']}"
					f"\n\t\tCustom filenames:\t{options['FILENAMES']['customfilenames']}")
			if strtobool(options["DUPLICATES"]["savepinid"]):
				with open(os.path.join(options["FOLDERS"]["saves"], "pinids.txt"), "w") as f:
					f.close()
			gstart = time.time()
			try:
				request(url)
			except IndexError:
				pass
			# except Exception as ex:
				# print(f"Something failed: {ex}")
			gend = time.time()
			print(f"\nFinished operation! Took {datetime.timedelta(seconds=gend - gstart)} seconds.")


def main():
	global debug
	loadConfig()

	try:
		opts, args = getopt.getopt(sys.argv[1:], 'd', ["debug="])
	except getopt.GetoptError as err:
		print(err)
		sys.exit()
	for o, a in opts:
		if o == '--debug':
			debug = a
		elif o == '-d':
			debug = True

	run()


if __name__ == '__main__':
	main()
