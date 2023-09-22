import numpy as np
import pytesseract
import cv2
from datetime import datetime, timedelta
import os
from flask import current_app
import requests

class MatcherAbstract:
	def __init__(self):
		self.ocr = Ocr()
		self._assets_path = os.path.join(current_app.root_path, "assets")

	def match(self, frame):
		pass


class IsAlive(MatcherAbstract):

	def __init__(self):
		super().__init__()
		self.template = cv2.imread(os.path.join(self._assets_path, 'templates/template-healthbarmask.png'), 0)

	def match(self, frame):
		healthbar_hls = cv2.cvtColor(frame[910:914,281:399], cv2.COLOR_BGR2HLS)
		Lchannel = healthbar_hls[:,:,1]
		area = cv2.inRange(Lchannel, 240, 255)
		result = cv2.matchTemplate(area, self.template, cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
		if (max_val == 0):
			return (False, {})
		return (True, {})


class ChampionMatcher(MatcherAbstract):

	def __init__(self):
		super().__init__()
		self._championImagesPath = os.path.join(self._assets_path, "champions/")
		self._loadChampions()

	def _resetResults(self):
		self._result = None
		self._value = 0

	def _loadChampions(self):
		self._championTemplates = {}
		files = os.listdir(self._championImagesPath)
		for file in files:
			if (file[0] != "."):
				self._championTemplates[file.replace(".png", "")] = self._loadTemplate(file)

	def _loadTemplate(self, template):
		return cv2.imread(self._championImagesPath + template, 0)

	def _evaluate(self, image, champion):
		result = cv2.matchTemplate(image, self._championTemplates[champion], cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
		# print(max_val, champion)
		if (max_val > self._value):
			self._value = max_val
			self._result = champion

	def identifyChampion(self, image):
		self._resetResults()
		if (len(image.shape) == 3):
			image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		for champion, championTemplate in self._championTemplates.items():
			self._evaluate(image, champion)
		return self._result

class Desktop(MatcherAbstract):
	def match(self, frame):
		template = cv2.imread(os.path.join(self._assets_path, 'icons/windows-icon.png'), 0)
		result = cv2.matchTemplate(cv2.cvtColor(frame[1043:1080, 0:37], cv2.COLOR_BGR2GRAY), template, cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
		if (max_val > 0.95):
			return (True, {})
		return (False, {})

class Desktop5Seconds(Desktop):
	def __init__(self):
		super().__init__()
		self.lastMatch = None

	def match(self, frame):
		match, data = super().match(frame)
		if (match):
			if (self.lastMatch is None):
				self.lastMatch = datetime.now()
				return (False, {})
			elif(self.lastMatch + timedelta(seconds=5) > datetime.now()):
				return (False, {})
			else:
				self.lastMatch = None
				return (True, {})
		else:
			self.lastMatch = None
			return (False, {})

class Scoreboard(MatcherAbstract):
	def __init__(self):
		super().__init__()
		self.template = cv2.imread(os.path.join(self._assets_path, "templates/duel.png"), 0)

	def match(self, frame):		
		res = cv2.matchTemplate(cv2.cvtColor(frame[40:140, 20:120], cv2.COLOR_BGR2GRAY), self.template, cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
		if (max_val > 0.96):
			return (True, {})
		return (False, {})

class DuelEndScoreboard(Scoreboard):
	def __init__(self):
		super().__init__()
	
	def match(self, frame):		
		match, data = super().match(frame)
		if (match):
			text = self.ocr.get_text_hsv(frame[0:45, 110:300], [0, 0, 163], [179, 255, 255]).replace("\n","")
			if any(word in text for word in ['Press', 'ESC', 'to', 'Skip']):
				return (True, {})
		return (False, {})


class MainMenu(MatcherAbstract):
	def __init__(self):
		super().__init__()
		self.template = cv2.imread(os.path.join(self._assets_path, 'templates/contacts.png'), 0)

	def match(self, frame):
		result = cv2.matchTemplate(cv2.cvtColor(frame[1030:1060, 130:240], cv2.COLOR_BGR2GRAY), self.template, cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
		if (max_val > 0.95): 
			return (True, {})
		return (False, {})


class MenuLoading(MatcherAbstract):
	def __init__(self):
		super().__init__()
		self.template = cv2.imread(os.path.join(self._assets_path, 'templates/menu-loading.png'), 0)

	def match(self, frame):
		result = cv2.matchTemplate(cv2.cvtColor(frame[480:680, 730:1200], cv2.COLOR_BGR2GRAY), self.template[480:680, 730:1200], cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
		if (max_val > 0.95): 
			return (True, {})
		return (False, {})

class WarmupEnd(MatcherAbstract):

	def __init__(self):
		super().__init__()
		self.champion_matcher = ChampionMatcher()
		self.ignore_bots = ["ezPotat", "HotButterBiscuit", "NoMeGrites"]

	def sanitize_player_name(self, name):
		return "".join([x for x in name if x.isalnum() or x.isspace() or x == '.'])

	def sanitize_map_name(self, name):
		return "".join([x for x in name if x.isalnum() or x.isspace()])


	def getPlayerChampion(self, frame):
		champImageSize = 56
		champY = 28
		champX = 679
		return self.champion_matcher.identifyChampion(frame[champY:champY+champImageSize, champX:champX+champImageSize])

	def getOpponentChampion(self, frame):
		champImageSize = 56
		champY = 28
		champX = 1182
		return self.champion_matcher.identifyChampion(frame[champY:champY+champImageSize, champX:champX+champImageSize])

	def player_exists(self, name):
		r = requests.get(f'https://quake-stats.bethesda.net/api/v2/Player/Search?term={name}')
		if (r.status_code == 200):
			for entity in r.json():
				if (entity.get('entityName') == name):
					return True
		return False

	def save_incorrect_ocr(self, frame):
		path = os.path.join(current_app.instance_path, 'incorrect_images')
		try:
		   os.makedirs(path)
		except FileExistsError:
		   pass # directory already exists
		cv2.imwrite(os.path.join(path, str(id(frame)) + '.png'), frame)

	def match(self, frame):
		hsv = cv2.cvtColor(frame[50:51, 920:921], cv2.COLOR_BGR2HSV)
		lower = np.array([0, 250, 220])
		higher = np.array([5, 255, 255])
		mask = cv2.inRange(hsv, lower, higher)
		if (mask[0,0] == 0):
			lower = np.array([175, 250, 220])
			higher = np.array([180, 255, 255])
			mask = cv2.inRange(hsv, lower, higher)
		if (mask[0,0] == 255):
			lower = np.array([0, 0, 92])
			higher = np.array([179, 60, 255])
			p_name = self.ocr.get_text_hsv(frame[92:114, 660:875], lower, higher).replace("\n", "")
			if (p_name == "SLAVE"):
				p_name = "SL4VE"
			o_name = self.ocr.get_text_hsv(frame[92:114, 1040:1238], lower, higher).replace("\n", "")
			if (not self.player_exists(p_name) or not self.player_exists(o_name)):
				self.save_incorrect_ocr(frame)
			if (o_name not in self.ignore_bots):
				return (True, {
					"p_champion": self.getPlayerChampion(frame),
					"o_champion": self.getOpponentChampion(frame),
					"p_name": self.sanitize_player_name(p_name),
					"o_name": self.sanitize_player_name(o_name)
					})
		return (False, {})

class MapLoading(MatcherAbstract):

	def __init__(self):
		super().__init__()
		self.mapTemplates = {
			"Awoken": cv2.imread(os.path.join(self._assets_path, 'maps/awoken.png'),0),
			"Blood Covenant": cv2.imread(os.path.join(self._assets_path, 'maps/bc.png'),0),
			"Crucible": cv2.imread(os.path.join(self._assets_path, 'maps/crucible.png'),0),
			"Corrupted Keep": cv2.imread(os.path.join(self._assets_path, 'maps/ck.png'),0),
			"Deep Embrace": cv2.imread(os.path.join(self._assets_path, 'maps/deep.png'),0),
			"Exile": cv2.imread(os.path.join(self._assets_path, 'maps/exile.png'),0),
			"Insomnia": cv2.imread(os.path.join(self._assets_path, 'maps/insomnia.png'), 0),
			"Molten Falls": cv2.imread(os.path.join(self._assets_path, 'maps/molten.png'),0),
			"Ruins of Sarnath": cv2.imread(os.path.join(self._assets_path, 'maps/ruins.png'),0),
			"Vale of Pnath": cv2.imread(os.path.join(self._assets_path, "maps/vale.png"), 0)
		}

	def match(self, frame):
		for map, template in self.mapTemplates.items():			
			result = cv2.matchTemplate(cv2.cvtColor(frame[105:155, 170:590], cv2.COLOR_BGR2GRAY), template[105:155, 170:590], cv2.TM_CCOEFF_NORMED)
			min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

			if (max_val > 0.95): 
				result = cv2.matchTemplate(cv2.cvtColor(frame[75:110, 170:800], cv2.COLOR_BGR2GRAY), template[75:110, 170:800], cv2.TM_CCOEFF_NORMED)
				min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
				if (max_val > 0.95):
					return (True, {'map': map})
		return (False, {})

class Ocr:
	def get_text_hsv(self, image, lower, upper):
		hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
		lower = np.array(lower)
		upper = np.array(upper)
		mask = cv2.inRange(hsv, lower, upper)
		result = 255 - mask
		whitelist = "0123456789qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM."
		return (pytesseract.image_to_string(result, lang='eng',config='--psm 6 --tessdata-dir ' + os.path.join(current_app.root_path, 'assets') + '  -c tessedit_char_whitelist=' + whitelist + ' -c page_separator=""'))
