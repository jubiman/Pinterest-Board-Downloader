import requests
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from lxml import html
from tkinter import filedialog


threads = []
saves = r".\downloaded"
mx_wrks = 25


def save(file, name, ext):
	if os.path.isfile(saves + name + ext):
		inp = input(f'Do you want to overwrite {name + ext}? y/n\t')
		if inp.lower() == 'n':
			return
	with open(saves + name + ext, 'wb') as f:
		f.write(file)
		f.close()


def requestImg(pin):
	try:
		p = requests.get(f'https://pinterest.com{pin}')

		script = html.fromstring(p.content).xpath('//script[@id="initial-state"]')
		js = json.loads(script[0].text)

		img_url = js["resourceResponses"][0]["response"]["data"]["images"]["orig"]["url"]
		name = js["resourceResponses"][0]["response"]["data"]["rich_metadata"]["title"]
		ext = img_url[img_url.rfind('.'):]

		# We do not want empty file names
		if not name or name == "":
			name = "unkown"

		return img_url, name, ext
	except requests.exceptions.RequestException as e:
		return e


def downloadImg(url, name, ext):
	# TODO: add options
	img = requests.get(url).content
	save(img, name, ext)


def request(url):
	# Create a web request to get the main JSON object from within the HTML code
	page = requests.get(url)
	# Get the JSON object string
	script = html.fromstring(page.content).xpath('//script[@id="initial-state"]')
	# Objectify the JSON object
	js = json.loads(script[0].text)

	# Create list of pins
	pins = js["resourceResponses"][1]["response"]["data"]

	# DEBUG
	with open("a.json", "w") as f:
		f.write(json.dumps(js["resourceResponses"][0], indent=4, sort_keys=True))
	with open("b.json", "w") as f:
		f.write(json.dumps(js["resourceResponses"][1], indent=4, sort_keys=True))

	# Multi-threading
	with ThreadPoolExecutor(max_workers=mx_wrks) as ex:
		# Go through each pin
		for pin in pins:
			"""
			if "/pin/" in pin:
				threads.append(ex.submit(requestImg, pin))
			"""
			# print(pin)
			if pin is None:
				continue

			# Some images don't have rich_metadata so we have to do another request
			if not pin["rich_metadata"]:
				# img_url = pin["images"]["orig"]["url"]
				# name = pin["rich_metadata"]["title"]
				# ext = img_url[img_url.rfind('.') + 1:]

				threads.append(ex.submit(requestImg, pin["seo_url"]))

			img_url = pin["images"]["orig"]["url"]
			name = pin["rich_metadata"]["title"]
			ext = img_url[img_url.rfind('.'):]

			print(img_url, name+ext)
			# We do not want empty file names
			if not name or name == "":
				name = "unkown"

			threads.append(ex.submit(downloadImg, (img_url, name, ext)))

		for task in as_completed(threads):
			# If the function returned successfully we can download the image
			if isinstance(task.result(), tuple):
				# downloadImg(*task.result())
				continue
			# The function failed to execute
			print(task.result())


if __name__ == '__main__':
	# url = input('Please input the url:\t')
	url = 'https://pinterest.com/humanAF/personal-top-favorites/'
	# saves = filedialog.askdirectory(title="Select a local folder where you want to put all the pinned pictures")
	request(url)

