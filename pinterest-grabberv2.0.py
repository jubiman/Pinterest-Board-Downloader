import asyncio
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
from traceback import print_exc

from getch import getch

import httpx
import requests
from lxml import html
from tkinter import filedialog

threads = {
	"imgprops": [],
	"download": []
}
options = ConfigParser()
debug = force = verbose = False
cls = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')
pinids = []
popup = True


class ImageData:
	def __init__(self, url, name, ext, iden):
		self.url = url
		self.name = name
		self.ext = ext
		self.id = iden


def configDefaults():
	options['FILENAMES']['customFileNames'] = 'True'
	options['FILENAMES']['customFileName'] = '@created_at'
	options['FILENAMES']['emptyFileName'] = ""
	options['MULTITHREADING']['mx_wrks'] = '0'
	options['FOLDERS']['saves'] = "./downloads"
	options['DUPLICATES']['checkforduplicates'] = "True"
	options['DUPLICATES']['savepinid'] = "True"
	options['DUPLICATES']['mode'] = "speed"
	options['DEBUG']['autologerrors'] = "False"
	options['DEBUG']['autoenabledebug'] = "False"

	saveConfig()


def loadConfig():
	global debug
	options.read('config.ini')
	if "DEBUG" not in options:
		options['DEBUG'] = {}
		options['DEBUG']['autologerrors'] = "False"
		options['DEBUG']['autoenabledebug'] = "False"
	elif "FILENAMES" not in options:
		options['FILENAMES'] = {}
		options['FILENAMES']['customFileNames'] = 'True'
		options['FILENAMES']['customFileName'] = '@created_at'
		options['FILENAMES']['emptyFileName'] = ""
	elif "MULTITHREADING" not in options:
		options['MULTITHREADING'] = {}
		options['MULTITHREADING']['mx_wrks'] = '0'
	elif "FOLDERS" not in options:
		options['FOLDERS'] = {}
		options['FOLDERS']['saves'] = "./downloads"
	elif "DUPLICATES" not in options:
		options['DUPLICATES'] = {}
		options['DUPLICATES']['checkforduplicates'] = "True"
		options['DUPLICATES']['savepinid'] = "True"
		options['DUPLICATES']['mode'] = "speed"

	if strtobool(options['DEBUG']['autoenabledebug']):
		debug = True


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
			k = ord(getch())
			if k in [ord('n'), ord('N')]:
				return
			elif k in [ord('y'), ord('Y')]:
				break
	with open(options['FOLDERS']['saves'] + '/' + name + ext, 'wb') as f:
		f.write(file)
		f.close()


def downloadImg(img, name, ext, iden):
	# TODO: add options
	save(img, name, ext)
	if strtobool(options["DUPLICATES"]["savepinid"]):
		with open(os.path.join(options["FOLDERS"]["saves"], "pinids.txt"), "r+") as f:
			if iden not in f.read().splitlines():
				f.write(iden)
				f.write("\n")
				f.close()


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

			script = html.fromstring(pin_page.content).xpath('//script[@id="__PWS_DATA__"]')
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
				img_url = obj["images"]["orig"]["url"]
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

			return img_url, name, ext, pin["id"]


def getImgProps(pin):
	if debug:
		with open("json_logs.json", "a") as f:
			f.write(json.dumps(pin, indent=4))
			f.write("\n\n")
			f.close()

	if pin['type'] != 'pin':
		return getImgPropsSpecial(pin)

	pin_page = requests.get(f"https://pinterest.com/pin/{pin['id']}")

	script = html.fromstring(pin_page.content).xpath('//script[@id="__PWS_DATA__')
	js = json.loads(script[0].text)
	if debug:
		with open("a.json", "w") as f:
			f.write(json.dumps(js, indent=4, sort_keys=False))
			f.close()

	img_url = ""
	if ('videos' in js["resourceResponses"][0]["response"]["data"]) and js["resourceResponses"][0]["response"]["data"]['videos']:
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
		except:
			name = str(randint(0, 1024))
	ext = img_url[img_url.rfind('.'):]
	# print(img_url, name + ext)
	# We do not want empty file names
	if not name or name == "":
		name = options["customFileName"]
	name = name.replace(':', '-')

	return img_url, name, ext, pin["id"]


async def dl(max_workers, reqs, tasks_list):
	downloaded = 0
	with ThreadPoolExecutor(max_workers=max_workers) as ex:
		for i, req in enumerate(reqs):
			threads["download"].append(ex.submit(downloadImg, req.content, tasks_list[i][1], tasks_list[i][2], tasks_list[i][3]))

		for _ in as_completed(threads["download"]):
			downloaded += 1
	return downloaded


async def request(board):
	if 'pinterest.com' in board:
		if 'https://' in board or 'http://' in board:
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
		script = html.fromstring(page.content).xpath('//script[@id="__PWS_DATA__"]')
		js = json.loads(script[0].text)
		board_id = js["props"]["initialReduxState"]["resources"]["BoardResource"][list(js["props"]["initialReduxState"]["resources"]["BoardResource"])[0]]["data"]["id"]
		timestamp = int(time.time() * 1000)
	except Exception as e:
		print("Failed to get board information. Exitting.")
		print_exc(chain=False)
		return


	url = 'https://pinterest.com/resource/BoardFeedResource/get/'
	bookmark = js["props"]["initialReduxState"]["resources"]["BoardFeedResource"][list(js["props"]["initialReduxState"]["resources"]["BoardFeedResource"])[0]]["nextBookmark"]
	pins = js["props"]["initialReduxState"]["resources"]["BoardFeedResource"][list(js["props"]["initialReduxState"]["resources"]["BoardFeedResource"])[0]]["data"]

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
		except requests.exceptions.RequestException:
			print_exc(chain=False)
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

	# Generate images (with a generator obeject)
	max_workers = None if int(options['MULTITHREADING']['mx_wrks']) == 0 else int(options['MULTITHREADING']['mx_wrks'])
	images, errors = await multithread(pins)

	# Multi-threading
	async with httpx.AsyncClient() as client:
		print(f"Downloading {len(pins)} images...")
		start2 = time.time()
		tasks = ((client.get(image.url), image.name, image.ext, image.id) for image in images)
		# task2 = []
		# for image in images:
		# 	task2.append((image.name, image.ext, image.id))

		reqs = await asyncio.gather(*(list(zip(*(tasks_list := list(tasks))))[0]))
		generated = len(reqs)
		end = time.time()
		print(f"Finished generating {len(pins)} images: generated {generated} images (Skipped {len(pins)-generated} with {errors} errors). Took {datetime.timedelta(seconds=end-start)}")
		downloaded = await dl(max_workers, reqs, tasks_list)
		end = time.time()
		print(f"Finished downloading {downloaded} images. Took {datetime.timedelta(seconds=end-start2)}")


async def multithread(pins):
	# with ThreadPoolExecutor(max_workers=max_workers) as ex:
	normal = special = []
	errors = 0
	# Go through each pin
	for pin in pins:
		if pin is None:
			continue

		if debug:
			with open("json_logs2.json", "a+") as f:
				f.write(json.dumps(pin, indent=4, sort_keys=True))
				f.write("\n\n")

		if strtobool(options["DUPLICATES"]["checkforduplicates"]):
			if options["DUPLICATES"]["mode"] == "speed":
				if pin["id"] in pinids:
					if verbose or debug:
						print(f"Skipping duplicate {pin['id']}")
					continue
			else:
				with open(os.path.join(options["FOLDERS"]["saves"], "pinids.txt"), "r") as f:
					if pin["id"] in f.read().splitlines():
						if verbose or debug:
							print(f"Skipping duplicate {pin['id']}")
						continue

		if pin['type'] != 'pin':
			special.append(pin["id"])
		elif pin["type"] == "pin":
			normal.append(pin["id"])
		else:
			print(f"wtf?? {pin['type']=}")

	imgs = []
	async with httpx.AsyncClient() as client:
		tasks = (client.get(f"https://pinterest.com/pin/{pinid}", follow_redirects=True) for pinid in normal)
		pin_pages = await asyncio.gather(*tasks)

		for pin_page in pin_pages:
			script = html.fromstring(pin_page.content).xpath('//script[@id="__PWS_DATA__"]')
			js = json.loads(script[0].text)

			with open("z.json", "w") as f:
				f.write(json.dumps(js, indent=4, sort_keys=not not 1))
			img_url = ""
			if js["props"]["initialReduxState"]["resources"]["PinResource"][list(js["props"]["initialReduxState"]["resources"]["PinResource"])[0]]["data"] is None:
				if debug:
					with open("wtf.json", "w") as f:
						f.write(json.dumps(js, indent=4, sort_keys=True))
				if strtobool(options['DEBUG']['autologerrors']) or debug:
					with open("error_logs.json", "a+", encoding="utf-16") as f:
						msg = js["props"]["initialReduxState"]["resources"]["PinResource"][list(js["props"]["initialReduxState"]["resources"]["PinResource"])[0]]["error"]["message"][js["props"]["initialReduxState"]["resources"]["PinResource"][list(js["props"]["initialReduxState"]["resources"]["PinResource"])[0]]["error"]["message"].find('"')+1:]
						msg = msg.replace('\\"', '"')
						msg = msg.replace('\\\\', '\\')
						try:
							js2 = json.loads(msg[:-1])
						except:
							print("Got an error while trying to load the error. Dumping json object to error_logs_error.json")
							f.write(json.dumps(js, indent=4, sort_keys=True))
						f.write(json.dumps(js2, indent=4, sort_keys=True, ensure_ascii=False))
					k = list(js["props"]["initialReduxState"]["resources"]["PinResource"])[0]
					path = "https://pinterest.com/pin/" + k[k.find("id=")+4:-1]
					print(f'Got an error while requesting {path}.'
							f'\n{js2["code"]} - {js2["message"]}'
							f'\nWrote the message object to error_logs.json')
					errors += 1
				continue
			if ('videos' in js["props"]["initialReduxState"]["resources"]["PinResource"][list(js["props"]["initialReduxState"]["resources"]["PinResource"])[0]]["data"]) and js["props"]["initialReduxState"]["resources"]["PinResource"][list(js["props"]["initialReduxState"]["resources"]["PinResource"])[0]]["data"]['videos']:
				if debug:
					with open("video.json", "w") as f:
						f.write(json.dumps(js, indent=4, sort_keys=True))
				v_d = js["props"]["initialReduxState"]["resources"]["PinResource"][list(js["props"]["initialReduxState"]["resources"]["PinResource"])[0]]["data"]['videos']['video_list']
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
				if debug:
					with open("x.json", "w") as f:
						f.write(json.dumps(js, indent=4, sort_keys=True))
				img_url = js["props"]["initialReduxState"]["resources"]["PinResource"][list(js["props"]["initialReduxState"]["resources"]["PinResource"])[0]]["data"]["images"]["orig"]["url"]
			try:
				name = dateConversion(
					js["props"]["initialReduxState"]["resources"]["PinResource"][list(js["props"]["initialReduxState"]["resources"]["PinResource"])[0]]["data"]["created_at"])  # ????? not works on 1 fsr
			except:
				try:
					name = js["props"]["initialReduxState"]["resources"]["PinResource"][list(js["props"]["initialReduxState"]["resources"]["PinResource"])[0]]["data"]["id"]
				except:
					name = str(randint(0, 1024))
			ext = img_url[img_url.rfind('.'):]
			# print(img_url, name + ext)
			# We do not want empty file names
			if not name or name == "":
				name = options["customFileName"]
			name = name.replace(':', '-')

			imgs.append(ImageData(img_url, name, ext, js["props"]["initialReduxState"]["resources"]["PinResource"][list(js["props"]["initialReduxState"]["resources"]["PinResource"])[0]]["data"]["id"]))
		return imgs, errors


def showSettings():
	print("Pinterest Board Downloader Settings\n")
	print("\t1. Filenames")
	print("\t2. Multi-threading")
	print("\t3. Folders")
	print("\t4. Duplicates")
	print("\t5. Debug options")
	print("\t9. Load defaults")
	print("\nCopyright (C) Jubiman 2021. All rights reserved. https://github.com/Jubiman/Pinterest-Board-Downloader/")
	print("\t\nESC. Return to console")

	k = ord(getch())
	
	if k == ord("1"):
		return showFilenames()
	elif k == ord("2"):
		return showMultithreading()
	elif k == ord("3"):
		return showFolders()
	elif k == ord("4"):
		return showDuplicates()
	elif k == ord("5"):
		return showDebugOptions()
	elif k == ord("9"):
		print("Are you sure you want to reset to defaults? y/n")
		k = ord(getch())
		if k in [ord('y'), ord('Y')]:
			configDefaults()
	elif k == 0x08 or k == 0x1b:
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
		k = ord(getch())
		if k == ord("1"):
			options['FILENAMES']['customFileNames'] = str(not strtobool(options['FILENAMES']['customFileNames']))
		elif k == ord("2"):
			val = input("New value:  ")
			options['FILENAMES']['customFileName'] = val
		elif k == 0x08 or k == 0x1b:
			cls()
			return showSettings()
		return showFilenames()


def showMultithreading():
	while True:
		cls()
		print("Pinterest Board Downloader Settings\n")
		print(f"\t1. Max workers (threads)\033[40G| [{options['MULTITHREADING']['mx_wrks']}]")
		print("\tESC. Back to main menu")
		k = ord(getch())
		if k == ord("1"):
			val = input("New value:  ")
			options['MULTITHREADING']['mx_wrks'] = val
		elif k == 0x08 or k == 0x1b:
			cls()
			return showSettings()
		return showMultithreading()


def showFolders():
	while True:
		cls()
		print("Pinterest Board Downloader Settings\n")
		print(f"\t1. Download folder\033[40G| [{options['FOLDERS']['saves']}]")
		print("\tESC. Back to main menu")
		k = ord(getch())
		if k == ord("1"):
			options['FOLDERS']['saves'] = filedialog.askdirectory(title="Select a local folder where you want to put "
																		"all the pinned pictures")
		elif k == 0x08 or k == 0x1b:
			cls()
			return showSettings()
		return showFolders()


def showDuplicates():
	while True:
		cls()
		print("Pinterest Board Downloader Settings\n")
		print(f"\t1. Check for duplicates\033[40G| [{options['DUPLICATES']['checkforduplicates']}]")
		print(f"\t2. Save pin ID\033[40G| [{options['DUPLICATES']['savepinid']}]")
		print(f"\t3. Efficiency mode\033[40G| [{options['DUPLICATES']['mode']}]")
		print("\tESC. Back to main menu")
		k = ord(getch())
		if k == ord("1"):
			options['DUPLICATES']['checkforduplicates'] = str(not strtobool(options['DUPLICATES']['checkforduplicates']))
		elif k == ord("2"):
			options['DUPLICATES']['savepinid'] = str(not strtobool(options['DUPLICATES']['savepinid']))
		elif k == ord("3"):
			if options['DUPLICATES']['mode'] == "speed":
				options['DUPLICATES']['mode'] = "memory"
				return showDuplicates()
			options['DUPLICATES']['mode'] = "speed"
			return showDuplicates()
		elif k == 0x08 or k == 0x1b:
			cls()
			return showSettings()
		return showDuplicates()


def showDebugOptions():
	while True:
		cls()
		print("Pinterest Board Downloader Settings\n")
		print(f"\t1. Log errors to error_logs.json\033[40G| [{options['DEBUG']['autologerrors']}]")
		print(f"\t2. Automatically enable debug mode\033[40G| [{options['DEBUG']['autoenabledebug']}]")
		print("\tESC. Back to main menu")
		k = ord(getch())
		if k == ord("1"):
			options['DEBUG']['checkforduplicates'] = str(not strtobool(options['DEBUG']['autologerrors']))
		elif k == ord("2"):
			options['DEBUG']['autoenabledebug'] = str(not strtobool(options['DEBUG']['autoenabledebug']))
		elif k == 0x08 or k == 0x1b:
			cls()
			return showSettings()
		return showDebugOptions()


def run():
	global debug
	global force
	global verbose
	global pinids
	global popup
	while True:
		# inp = input("$>")
		inp = "dl https://pinterest.com/humanAF/art-n-stuff/ -f -n -d"  # DEBUG
		if inp.lower() == "settings":
			showSettings()
		if inp.lower() == "quit" or inp.lower() == "exit":
			sys.exit(0)
		s = inp.split()
		if s[0] in ["download", 'dl']:
			url = s[1]
			try:
				opts, args = getopt.getopt(s[2:], 'dfvn', ["debug", "force", "verbose", "no-dir"])
			except getopt.GetoptError as err:
				print(err)
				continue
			for o, a in opts:
				if o == '--force':
					force = True
				elif o == '-f':
					force = True
				if o == '--debug':
					debug = True
				elif o == '-d':
					debug = True
				if o == '--verbose':
					verbose = True
				elif o == '-v':
					verbose = True
				if o == '-n':
					popup = False
				elif o == '--no-dir':
					popup = False

			if popup:
				options['FOLDERS']['saves'] = filedialog.askdirectory(
					title="Select a local folder where you want to put all the pinned pictures")

			# TODO: add more stuff?
			print(f"Starting operation: downloading board from {url}.\n\tArguments:\n\t\t-f FORCE {force}\n\t\t-d DEBUG {debug}"
					f"\n\t\t-v VERBOSE {verbose}\n\t\t-n NO-DIR {not popup}"
					f"\n\tOptions:\n\t\tCheck for duplicates:\t{options['DUPLICATES']['checkforduplicates']}"
					f"\n\t\tMode:\t\t\t{options['DUPLICATES']['mode']}"
					f"\n\t\tDownload folder:\t\"{options['FOLDERS']['saves']}\"\n\t\tMax threads:\t\t{options['MULTITHREADING']['mx_wrks']}"
					f"\n\t\tCustom filenames:\t{options['FILENAMES']['customfilenames']}")
			if not os.path.isdir(options["FOLDERS"]["saves"]):
				os.mkdir(options["FOLDERS"]["saves"])
			if strtobool(options["DUPLICATES"]["savepinid"]):
				open(os.path.join(options["FOLDERS"]["saves"], "pinids.txt"), "a+").close()
			if options["DUPLICATES"]["mode"] == "speed":
				with open(os.path.join(options["FOLDERS"]["saves"], "pinids.txt"), "r") as f:
					pinids = f.read().splitlines()
					f.close()
			saveConfig()

			gstart = time.time()
			try:
				asyncio.run(request(url))
			except IndexError:
				print_exc()
			# except Exception as ex:
				# print(f"Something failed: {ex}")
			gend = time.time()
			print(f"\nFinished operation! Took {datetime.timedelta(seconds=gend - gstart)} seconds.")
		else:
			print(f"Command not found.")


def main():
	global debug
	loadConfig()

	try:
		opts, args = getopt.getopt(sys.argv[1:], 'd', ["debug"])
	except getopt.GetoptError as err:
		print(err)
		sys.exit()
	for o, a in opts:
		if o == '--debug':
			debug = True
		elif o == '-d':
			debug = True

	run()


if __name__ == '__main__':
	main()
