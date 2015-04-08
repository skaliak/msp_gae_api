from google.appengine.ext import ndb


class Monster(ndb.Model):
	name = ndb.StringProperty(required=True)
	description = ndb.StringProperty(required=True)
	image_url = ndb.StringProperty()
	created_by = ndb.UserProperty()


class Sighting(ndb.Model):
	timestamp = ndb.DateTimeProperty(required=True)
	location = ndb.GeoPtProperty(required=True)
	sighted_by = ndb.UserProperty()
	notes = ndb.StringProperty()

	@classmethod
	def query_area(self, ne_str, sw_str):
		"""
		+------------------ne
		|					|
		|					|
		|		loc         |
		|					|
		|					|
		sw------------------|
		
		"""
		ne = ndb.GeoPt(ne_str)
		sw = ndb.GeoPt(sw_str)
		q = self.query()
		q = q.filter(Sighting.location < ne)
		q = q.filter(Sighting.location > sw)
		return q
