from flask import current_app
import zmq

class Message:
	def __init__(self, service = None, action = None):
		self.service = service
		self.action = action

class Client:

	def send_message(self, message):
		socket = zmq.Context().socket(zmq.REQ)
		socket.connect('tcp://127.0.0.1:5000')
		socket.send_json({
			'service': message.service,
			'action': message.action,
		})
		response = socket.recv_json()
		current_app.logger.info(response)

	def start_service(self, name):
		self.send_message(Message(name, 'start'))

	def stop_service(self, name):
		self.send_message(Message(name, 'stop'))

class Server:
	zmq_port = 5000

	def __init__(self, available_services = None):
		self.zmq = zmq.Context().socket(zmq.REP)
		self.zmq.bind('tcp://127.0.0.1:' + str(self.zmq_port))
		self.zmq_pending_response = False
		if (available_services is None):
			self.available_services = []
		else: 
			self.available_services = available_services

	def get_request_json(self):
		if (self.zmq_pending_response):
			return None
		try:
			json = self.zmq.recv_json(flags=zmq.NOBLOCK)
			self.zmq_pending_response = True
			return json
		except zmq.Again:
			return None
		
	def respond(self, result, data = None):
		if (data is None):
			data = {}
		if (self.zmq_pending_response):
			self.zmq.send_json({'success': result} | data)
			self.zmq_pending_response = False

	def respond_success(self):
		self.respond(True)

	def respond_fail(self, errors = None):
		self.respond(False, {'errors': errors})

	def shutdown(self):
		self.respond_success()

	def validate_request(self, json):
		service = json['service'] if 'service' in json else None
		errors = []
		if (service is None):
			errors.append("No service specified")
		if (service not in self.available_services):
			errors.append(f"service {service} does not exist")
		action = json['action'] if 'action' in json else None
		if (action is None):
			errors.append("No action specified")
		if (action not in ["start", "stop"]):
			errors.append(f"Action {action} is invalid")
		if (errors):
			return (False, errors)
		return (True, None)

	def get_message(self):
		json = self.get_request_json()
		if (json is None):
			return None
		result, data = self.validate_request(json)
		if (result == False):
			self.respond_fail(data)
			return None
		service = json['service']
		action = json['action']
		return Message(service, action)
		# if (service == 'core' and action == 'stop'):
		# 	signal('app-shutdown').send(self)
		# 	return
		# else:
		# 	if (action == 'start'):
		# 		current_app.logger.info(f"Starting {service}")
		# 		self.service_manager.start_service(service)
		# 	if (action == 'stop'):
		# 		current_app.logger.info(f"Stopping {service}")
		# 		self.service_manager.stop_service(service)
		# self.respond_success()
