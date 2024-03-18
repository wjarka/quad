import numpy as np
import pytesseract
import cv2
from datetime import datetime, timedelta
import os
from flask import current_app


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
		if max_val == 0:
			return False, {}
		return True, {}


class ChampionMatcher(MatcherAbstract):

	def __init__(self):
		super().__init__()
		self._load_champions()

	def _reset_results(self):
		self._result = None
		self._value = 0

	def _load_champions(self):
		self._championTemplates = {}
		from .extensions import db
		from .models import Champion
		from sqlalchemy import select
		champions = db.session.scalars(select(Champion))
		for champion in champions:
			self._championTemplates[champion.name] = cv2.imread(os.path.join(current_app.root_path, champion.template_path), 0)

	def _evaluate(self, image, champion):
		result = cv2.matchTemplate(image, self._championTemplates[champion], cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
		if max_val > self._value:
			self._value = max_val
			self._result = champion

	def identify_champion(self, image):
		self._reset_results()
		if len(image.shape) == 3:
			image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		for champion, championTemplate in self._championTemplates.items():
			self._evaluate(image, champion)
		return self._result


class Desktop(MatcherAbstract):
	def match(self, frame):
		template = cv2.imread(os.path.join(self._assets_path, 'icons/windows-icon.png'), 0)
		result = cv2.matchTemplate(cv2.cvtColor(frame[1043:1080, 0:37], cv2.COLOR_BGR2GRAY), template, cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
		if max_val > 0.95:
			return True, {}
		return False, {}


class Desktop5Seconds(Desktop):
	def __init__(self):
		super().__init__()
		self.lastMatch = None

	def match(self, frame):
		match, data = super().match(frame)
		if match:
			if self.lastMatch is None:
				self.lastMatch = datetime.now()
				return False, {}
			elif self.lastMatch + timedelta(seconds=5) > datetime.now():
				return False, {}
			else:
				self.lastMatch = None
				return True, {}
		else:
			self.lastMatch = None
			return False, {}


class Scoreboard(MatcherAbstract):
	def __init__(self):
		super().__init__()
		self.template = cv2.imread(os.path.join(self._assets_path, "templates/duel.png"), 0)

	def match(self, frame):		
		res = cv2.matchTemplate(cv2.cvtColor(frame[40:140, 20:120], cv2.COLOR_BGR2GRAY), self.template, cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
		if max_val > 0.96:
			return True, {}
		return False, {}


class DuelEndScoreboard(Scoreboard):
	def __init__(self):
		super().__init__()
	
	def match(self, frame):		
		match, data = super().match(frame)
		if match:
			text = self.ocr.get_text_hsv(frame[0:45, 110:300], [0, 0, 163], [179, 255, 255]).replace("\n","")
			if any(word in text for word in ['Press', 'ESC', 'to', 'Skip']):
				return True, {}
		return False, {}


class MainMenu(MatcherAbstract):
	def __init__(self):
		super().__init__()
		self.template = cv2.imread(os.path.join(self._assets_path, 'templates/contacts.png'), 0)

	def match(self, frame):
		result = cv2.matchTemplate(cv2.cvtColor(frame[1030:1060, 130:240], cv2.COLOR_BGR2GRAY), self.template, cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
		if max_val > 0.95:
			return True, {}
		return False, {}


class MenuLoading(MatcherAbstract):
	def __init__(self):
		super().__init__()
		self.template = cv2.imread(os.path.join(self._assets_path, 'templates/menu-loading.png'), 0)

	def match(self, frame):
		result = cv2.matchTemplate(cv2.cvtColor(frame[480:680, 730:1200], cv2.COLOR_BGR2GRAY), self.template[480:680, 730:1200], cv2.TM_CCOEFF_NORMED)
		min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
		if max_val > 0.95:
			return True, {}
		return False, {}


class WarmupEnd(MatcherAbstract):
	def __init__(self):
		super().__init__()
		self.champion_matcher = ChampionMatcher()
		self.ignore_bots = ["ezPotat", "HotButterBiscuit", "NoMeGrites"]
		from .common import QuakeStats
		self.stats = QuakeStats()

	def sanitize_player_name(self, name):
		return "".join([x for x in name if x.isalnum() or x.isspace() or x == '.'])

	def sanitize_map_name(self, name):
		return "".join([x for x in name if x.isalnum() or x.isspace()])

	def get_player_champion(self, frame):
		champImageSize = 56
		champY = 28
		champX = 679
		return self.champion_matcher.identify_champion(frame[champY:champY + champImageSize, champX:champX + champImageSize])

	def get_opponent_champion(self, frame):
		champImageSize = 56
		champY = 28
		champX = 1182
		return self.champion_matcher.identify_champion(frame[champY:champY + champImageSize, champX:champX + champImageSize])

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
		if mask[0,0] == 0:
			lower = np.array([175, 250, 220])
			higher = np.array([180, 255, 255])
			mask = cv2.inRange(hsv, lower, higher)
		if mask[0,0] == 255:
			lower = np.array([0, 0, 92])
			higher = np.array([179, 60, 255])
			p_name = self.ocr.get_text_hsv(frame[92:114, 660:875], lower, higher).replace("\n", "")
			if p_name == "SLAVE":
				p_name = "SL4VE"
			o_name = self.ocr.get_text_hsv(frame[92:114, 1040:1238], lower, higher).replace("\n", "")
			if not self.stats.player_exists(p_name) or not self.stats.player_exists(o_name):
				self.save_incorrect_ocr(frame)
			if o_name not in self.ignore_bots:
				return True, {
					"player_champion_id": self.get_player_champion(frame),
					"opponent_champion_id": self.get_opponent_champion(frame),
					"player_name": self.sanitize_player_name(p_name),
					"opponent_name": self.sanitize_player_name(o_name)
					}
		return False, {}


class MapLoading(MatcherAbstract):

	def __init__(self):
		super().__init__()
		self._load_templates()

	def _load_templates(self):
		from .extensions import db
		from .models import Map
		from sqlalchemy import select
		maps = db.session.scalars(select(Map))
		self.mapTemplates = {}
		for map in maps:
			self.mapTemplates[map.code] = cv2.imread(os.path.join(current_app.root_path, map.template_path), 0)

	def match(self, frame):
		for map, template in self.mapTemplates.items():			
			result = cv2.matchTemplate(cv2.cvtColor(frame[105:155, 170:590], cv2.COLOR_BGR2GRAY), template[105:155, 170:590], cv2.TM_CCOEFF_NORMED)
			min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

			if max_val > 0.95:
				result = cv2.matchTemplate(cv2.cvtColor(frame[75:110, 170:800], cv2.COLOR_BGR2GRAY), template[75:110, 170:800], cv2.TM_CCOEFF_NORMED)
				min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
				if max_val > 0.95:
					return True, {'map_id': map}
		return False, {}


class Ocr:
	def get_text_hsv(self, image, lower, upper):
		hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
		lower = np.array(lower)
		upper = np.array(upper)
		mask = cv2.inRange(hsv, lower, upper)
		result = 255 - mask
		whitelist = "0123456789qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM."
		return pytesseract.image_to_string(result, lang='eng',config='--psm 6 --tessdata-dir ' + os.path.join(current_app.root_path, 'assets') + '  -c tessedit_char_whitelist=' + whitelist + ' -c page_separator=""')
