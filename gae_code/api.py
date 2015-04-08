import webapp2
import json
import datetime
import random
from logging import debug, error
from models import *
from google.appengine.api import users
from google.appengine.api import oauth

"""
http status codes:
201: created
204: deleted/updated
400: bad request
405: method not allowed
501: not implemented
405: method not allowed
"""


#decorator
def auth_required(fn):
	def new_fn(*args, **kwargs):
		self = args[0]
		user = users.get_current_user()
		if not user:
			self.response.status_int = 403
		else:
			self.user = user
			fn(*args, **kwargs)
	return new_fn


#decorator
def auth_optional(fn):
	def new_fn(*args, **kwargs):
		self = args[0]
		user = users.get_current_user()
		if user:
			debug("user is " + str(user))
			self.user = user
		fn(*args, **kwargs)
	return new_fn


#decorator
def try_oauth(fn):
	def new_fn(*args, **kwargs):
		self = args[0]
		try:
			user = oauth.get_current_user()
			if user:
				self.user = user
		except oauth.OAuthRequestError, e:
			error(str(e))
		fn(*args, **kwargs)
	return new_fn


class Generic_Resource(webapp2.RequestHandler):
	T = ndb.Model

	def get_entity(self, encoded_key):
		if encoded_key:
			try:
				key = ndb.Key(urlsafe=encoded_key)
			except Exception:
				self.abort(404)
			if key:
				entity = key.get()
			else:
				self.abort(404)
		else:
			self.abort(400)
		return entity

	def finalize_create(self, dict_kwargs):
		new_ent = self.T(**dict_kwargs)
		new_ent.put()
		output = self.entity_to_dict(new_ent)
		output['encoded_key'] = new_ent.key.urlsafe()
		self.response.headers.add_header("Access-Control-Allow-Origin", "*")
		self.response.status_int = 201
		self.response.headers['Content-Type'] = 'application/json'
		self.response.write(json.dumps(output))

	def entity_to_dict(self, entity):
		entity_dict = entity.to_dict()
		entity_dict['encoded_key'] = entity.key.urlsafe()
		parent_key = entity.key.parent()
		if parent_key:
			#debug("entity has a parent, adding to dict")
			parent = parent_key.get()
			if not parent:
				#orphaned
				debug(str(entity.key) + " is an orphan, deleting")
				parent_key.delete()
				entity.key.delete()
				return None
			entity_dict['parent'] = parent_key.urlsafe()
			entity_dict['parent_name'] = parent.name
		if 'location' in entity_dict:
			geopt_obj = entity_dict['location']
			loc_string = str(geopt_obj.lat) + "," + str(geopt_obj.lon)
			entity_dict['location'] = loc_string
			entity_dict['lat'] = geopt_obj.lat
			entity_dict['lng'] = geopt_obj.lon
		if 'timestamp' in entity_dict:
			entity_dict['timestamp'] = str(entity_dict['timestamp'])
		created_by = entity_dict.get('created_by')
		if created_by:
			#debug("converting UserProperty object...")
			entity_dict['created_by'] = entity_dict['created_by'].nickname()
		return entity_dict

	@auth_optional
	def get(self, encoded_key=None):
		u = getattr(self, 'user', None)
		if encoded_key:
			entity = self.get_entity(encoded_key)
			output = self.entity_to_dict(entity)
		else:
			if u and self.T == Monster:
				debug("lookup by user")
				all_entities = self.T.query(self.T.created_by == u).fetch()
			else:
				all_entities = self.T.query().fetch()
			output = []
			for m in all_entities:
				d = self.entity_to_dict(m)
				if d:
					output.append(d)
		self.response.headers.add_header("Access-Control-Allow-Origin", "*")
		self.response.headers['Content-Type'] = 'application/json'
		self.response.write(json.dumps(output))
		self.response.md5_etag()

	#@auth_required
	@auth_optional
	def post(self, placeholder=None):
		debug("post called")
		if placeholder:
			self.abort(400)
		json_string = self.request.body
		posted_object = json.loads(json_string)
		#sanatize/check input first?
		u = getattr(self, 'user', None)
		if u:
			debug("user set to " + str(u))
			posted_object['created_by'] = u
		self.finalize_create(posted_object)

	def put(self, encoded_key):
		try:
			entity = self.get_entity(encoded_key)
		except Exception:
			self.abort(404)
		json_string = self.request.body
		posted_object = json.loads(json_string)
		keys_to_remove = ['encoded_key', 'parent', 'parent_name', 'timestamp', 'location', 'created_by', 'sighted_by']
		for k in keys_to_remove:
			if k in posted_object:
				del posted_object[k]
		entity.populate(**posted_object)
		entity.put()
		self.response.status_int = 204

	def delete(self, encoded_key):
		try:
			entity = self.get_entity(encoded_key)
		except Exception:
			self.abort(404)
		if entity:
			entity.key.delete()
			self.response.status_int = 204
		else:
			self.response.status_int = 404

	def options(self, m_encoded_key=None, encoded_key=None):
		self.response.headers.add_header("Access-Control-Allow-Origin", "*")
		self.response.headers.add_header("Access-Control-Allow-Headers", "Content-Type")
		self.response.status_int = 200


class Monsters(Generic_Resource):
	def __init__(self, *arg):
		self.T = Monster
		super(Monsters, self).__init__(*arg)

	def delete(self, encoded_key):
		try:
			key = ndb.Key(urlsafe=encoded_key)
		except Exception:
			self.abort(404)
		all_children = Sighting.query(ancestor=key)
		for k in all_children.iter(keys_only=True):
			k.delete()
		key.delete()
		self.response.status_int = 204


class Sightings(Generic_Resource):
	def __init__(self, *arg):
		self.T = Sighting
		super(Sightings, self).__init__(*arg)

	def return_results(self, entities):
		self.response.headers.add_header("Access-Control-Allow-Origin", "*")
		if len(entities) > 0:
			output = []
			for m in entities:
				d = self.entity_to_dict(m)
				output.append(d)
			self.response.headers['Content-Type'] = 'application/json'
			self.response.write(json.dumps(output))
		else:
			self.response.status_int = 204

	def get(self, m_encoded_key=None, s_encoded_key=None):
		if m_encoded_key:
			parent_key = ndb.Key(urlsafe=m_encoded_key)
			all_entities = self.T.query(ancestor=parent_key).fetch()
			self.return_results(all_entities)

		elif ('ne' in self.request.GET) and ('sw' in self.request.GET):
			debug("*** doing a geosearch ***")
			ne = self.request.get('ne')
			sw = self.request.get('sw')
			q = Sighting.query_area(ne, sw)
			all_entities = q.fetch()
			# all_entities = Sighting.query_area(ne, sw)
			self.return_results(all_entities)

		else:
			super(Sightings, self).get(s_encoded_key)

	def post(self, m_encoded_key=None, s_encoded_key=None):
		if m_encoded_key:
			parent_key = ndb.Key(urlsafe=m_encoded_key)
			json_string = self.request.body
			posted_object = json.loads(json_string)
			#debug(posted_object)

			#convert geopt and timestamp...
			try:
				#original format: '%Y-%m-%d %H:%M:%S.%f'
				dt = datetime.datetime.strptime(posted_object['timestamp'], '%Y-%m-%d %H:%M:%S')
			except:
				try:
					debug("used backup date format")
					dt = datetime.datetime.strptime(posted_object['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
				except:
					debug("used second backup date format")
					dt = datetime.datetime.strptime(posted_object['timestamp'], '%a, %d %b %Y %H:%M:%S %Z')
			posted_object['timestamp'] = dt
			lat = posted_object.pop('lat', None)
			lng = posted_object.pop('lng', None)
			if lat and lng:
				loc = ndb.GeoPt(lat, lng)
			else:
				loc = ndb.GeoPt(posted_object['location'])
			posted_object['location'] = loc
			posted_object['parent'] = parent_key
			posted_object.pop('pid', None)

			self.finalize_create(posted_object)
		else:
			self.abort(400)

	def delete(self, m_encoded_key=None, s_encoded_key=None):
		super(Sightings, self).delete(s_encoded_key)

	def put(self, m_encoded_key=None, s_encoded_key=None):
		super(Sightings, self).put(s_encoded_key)	


class RedirectHandler(webapp2.RequestHandler):
	def get(self):
		self.redirect('/index.html#/monsters')

class LoginHandler(webapp2.RequestHandler):
	def get(self):
		self.redirect(users.create_login_url())

class LogoutHandler(webapp2.RequestHandler):
	def get(self):
		self.redirect(users.create_logout_url())


app = webapp2.WSGIApplication([
	webapp2.Route('/', handler=RedirectHandler, name='redirect'),
	webapp2.Route('/login', handler=LoginHandler, name='login'),
	webapp2.Route('/logout', handler=LogoutHandler, name='logout'),
	webapp2.Route('/api/v1/Monsters/', handler=Monsters, name='all_monsters'),
	webapp2.Route('/api/v1/Monsters/<encoded_key>', handler=Monsters, name='monsters'),
	webapp2.Route('/api/v1/Monsters/<m_encoded_key>/Sightings/', handler=Sightings, name='sightings_of_monster'),
	webapp2.Route('/api/v1/Monsters/Sightings/', handler=Generic_Resource, name='options', methods=['OPTIONS']),
	webapp2.Route('/api/v1/Sightings/', handler=Sightings, name='all_sightings', methods=['GET']),
	webapp2.Route('/api/v1/Sightings/<s_encoded_key>', handler=Sightings, name='sightings', methods=['GET', 'PUT', 'DELETE'])
], debug=True)