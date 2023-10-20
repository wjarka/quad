import http.client as httplib
import httplib2
import os
import random
import time
from .common import Game
import logging
import json
from flask import current_app

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets, OAuth2WebServerFlow
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


class YouTubeUploader:

	# Explicitly tell the underlying HTTP transport library not to retry, since
	# we are handling retry logic ourselves.
	httplib2.RETRIES = 1

	# Maximum number of times to retry before giving up.
	MAX_RETRIES = 10

	# Always retry when these exceptions are raised.
	RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
		httplib.IncompleteRead, httplib.ImproperConnectionState,
		httplib.CannotSendRequest, httplib.CannotSendHeader,
		httplib.ResponseNotReady, httplib.BadStatusLine)

	# Always retry when an apiclient.errors.HttpError with one of these status
	# codes is raised.
	RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

	# This OAuth 2.0 access scope allows an application to upload files to the
	# authenticated user's YouTube channel, but doesn't allow other types of access.
	YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
	YOUTUBE_API_SERVICE_NAME = "youtube"
	YOUTUBE_API_VERSION = "v3"

	# This variable defines a message to display if the CLIENT_SECRETS_FILE is
	# missing.
	MISSING_CLIENT_SECRETS_MESSAGE = """
	WARNING: Please configure OAuth 2.0

	To make this sample run you will need to populate the client_secrets.json

	with information from the API Console
	https://console.cloud.google.com/

	For more information about the client_secrets.json file format, please visit:
	https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
	"""


	VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

	def __init__(self):
		self.service = self.get_authenticated_service()

	def prepare_flow(self):
		# Grab settings from the client_secrets.json file provided by Google
		secrets_file_path = current_app.instance_path + "/youtube/client_secrets.json"
		with open(secrets_file_path, 'r') as fp:
			obj = json.load(fp)

		# The secrets we need are in the 'web' node
		secrets = obj['installed']

		# Return a Flow that requests a refresh_token
		return OAuth2WebServerFlow(
			client_id=secrets['client_id'],
			client_secret=secrets['client_secret'],
			scope=self.YOUTUBE_UPLOAD_SCOPE,
			redirect_uri=secrets['redirect_uris'][0],
			access_type='offline',
			prompt='consent')


	def get_authenticated_service(self):
		# flow = flow_from_clientsecrets(self.CLIENT_SECRETS_FILE,
		# scope=self.YOUTUBE_UPLOAD_SCOPE,
		# message=self.MISSING_CLIENT_SECRETS_MESSAGE)
		flow = self.prepare_flow()

		storage = Storage(current_app.instance_path + "/youtube/credentials.storage")
		credentials = storage.get()

		
		if credentials is None:
			args = argparser.parse_args()
			args.noauth_local_webserver = True
			credentials = run_flow(flow, storage, args)

		if credentials.invalid:
			credentials.refresh(httplib2.Http())

		return build(self.YOUTUBE_API_SERVICE_NAME, self.YOUTUBE_API_VERSION,
			http=credentials.authorize(httplib2.Http()))

	def initialize_upload(self, options):
		tags = None
		if options.keywords:
			tags = options.keywords.split(",")

		body=dict(
			snippet=dict(
				title=options.title,
				description=options.description,
				tags=tags,
				categoryId=options.category
			),
			status=dict(
				privacyStatus=options.privacyStatus
			)
		)

		# Call the API's videos.insert method to create and upload the video.
		insert_request = self.service.videos().insert(
			part=",".join(body.keys()),
			body=body,
			# The chunksize parameter specifies the size of each chunk of data, in
			# bytes, that will be uploaded at a time. Set a higher value for
			# reliable connections as fewer chunks lead to faster uploads. Set a lower
			# value for better recovery on less reliable connections.
			#
			# Setting "chunksize" equal to -1 in the code below means that the entire
			# file will be uploaded in a single HTTP request. (If the upload fails,
			# it will still be retried where it left off.) This is usually a best
			# practice, but if you're using Python older than 2.6 or if you're
			# running on App Engine, you should set the chunksize to something like
			# 1024 * 1024 (1 megabyte).
			media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
		)

		return self.resumable_upload(insert_request)

	# This method implements an exponential backoff strategy to resume a
	# failed upload.
	def resumable_upload(self, insert_request):
		response = None
		error = None
		retry = 0
		while response is None:
			try:
				print("Uploading file...")
				status, response = insert_request.next_chunk()
				if response is not None:
					if 'id' in response:
						logging.info("Video id '%s' was successfully uploaded." % response['id'])
					else:
						logging.warn("The upload failed with an unexpected response: %s" % response)
						return None
			except HttpError as e:
				if e.resp.status in self.RETRIABLE_STATUS_CODES:
					error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
				else:
					raise
			except self.RETRIABLE_EXCEPTIONS as e:
				error = "A retriable error occurred: %s" % e

			if error is not None:
				logging.error(error)
				retry += 1
				if retry > self.MAX_RETRIES:
					logging.info("No longer attempting to retry.")
					return None

				max_sleep = 2 ** retry
				sleep_seconds = random.random() * max_sleep
				logging.info("Sleeping %f seconds and then retrying..." % sleep_seconds)
				time.sleep(sleep_seconds)
		return response['id']

	def upload(self, game):
		options = UploadOptions.from_game(game)
		try:
			vid = self.initialize_upload(options)
			return f'https://youtube.com/watch?v={vid}'
		except HttpError as e:
			logging.error("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))


class UploadOptions:
	def __init__(self):
		self.file = None
		self.title = None
		self.description = ""
		self.category = 20
		self.keywords = ""
		self.privacyStatus = "unlisted"

	@classmethod
	def from_game(cls, game:Game):
		o = UploadOptions()
		o.file = game.get('recording_path')
		o.title = game.get('player_name') + " (" + game.get('player_champion').name + ") vs " + game.get('opponent_name') + " (" + game.get('opponent_champion').name + ") " + game.get('map').name + " (" + game.get('timestamp').strftime("%Y-%m-%d-%H-%M-%S") + ")"
		o.description = "Recorded with NDI QC Recorder by SL4VE"
		o.keywords = ','.join([game.get('player_champion').name, game.get('opponent_champion').name, game.get('map').name])
		return o
