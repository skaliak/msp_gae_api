"""
Peter Lindberg
cs496 w15
Assignment 3: part 2
unit tests
"""

import unittest
import requests
import datetime
import time
import random
import json


#BASE_URL = "http://monspotting.appspot.com/api/v1"
BASE_URL = "http://localhost:8080/api/v1"
MONSTER_PATH = "/Monsters/"
SIGHTING_PATH = "/Sightings/"
MONSTER_MODEL = {"encoded_key": unicode, "name": unicode, "description": unicode, "image_url": unicode, "created_by": unicode}
MONSTER_MODEL_NULLABLE = ["image_url", "created_by"]
SIGHTING_MODEL = {"encoded_key": unicode, "timestamp": unicode, "location": unicode, "sighted_by": unicode, "notes": unicode}
SIGHTING_MODEL_NULLABLE = ["notes", "sighted_by"]
encoded_keys = []
sample_keys = {'monster': "", 'sighting': ""}
testing_monster_key = ""
names = ["joe", "frank", "george", "hugo", "oliver", "fred", "stew", "jerry"]
surnames = [" the ugly", " the sticky", " the squishy", " from cleveland", " monster"]

accumulating = False
skip_extra_tests = True
fresh_dev_server = False

class AllTests(unittest.TestCase):

    def _check_dict_format(self, d, format_spec, nullable):
        self.assertIsInstance(d, dict)
        for k in format_spec:
            if k not in d:
                self.assertIn(k, nullable, "required property " + k + " is missing")
            else:
                if d[k]:
                    self.assertIsInstance(d[k], format_spec[k], k + " is the wrong type: " + str(type(d[k])) + " " + str(d[k]))
                else:
                    self.assertIn(k, nullable, "required property " + k + " is null")

    def _ununicode(self, original_dict):
        """
        convert all keys and values from unicode to str
        :param original_dict: any dict with values that all have a __str__() method
        :return: dict with all values as str
        """
        new_dict = {}
        for k, v in original_dict.iteritems():
            if v is None:
                new_dict[str(k)] = None
            else:
                new_dict[str(k)] = str(v)
        return new_dict

    def _generic_get_test(self, urlpath, model, nullable, ent_type, multi=True, path_postfix=""):
        global sample_keys
        if multi:
            if len(path_postfix) > 0:
                key = sample_keys['monster']
                url = BASE_URL + urlpath + key + path_postfix
            else:
                url = BASE_URL + urlpath
            r = requests.get(url)
            self.assertEqual(r.status_code, 200, "expected status code 200, got " + str(r.status_code))
            list_of_dicts = r.json()

            self.assertIsInstance(list_of_dicts, list, "expected a list")
            for d in list_of_dicts:
                self._check_dict_format(d, model, nullable)
            if len(path_postfix) == 0 and len(list_of_dicts) > 0:   # don't let sighting key overwrite monster key
                sample_keys[ent_type] = list_of_dicts[0]["encoded_key"]
        else:
            encoded_key = sample_keys[ent_type]
            if len(encoded_key) == 0:
                self.fail("fail! no keys to test")
            else:
                url = BASE_URL + urlpath + encoded_key
                r = requests.get(url)
                self.assertEqual(r.status_code, 200, "expected status code 200, got " + str(r.status_code))
                d = r.json()
                self.assertIsInstance(d, dict, "expected a dict to be returned, instead got " + str(d))
                self._check_dict_format(d, model, nullable)

    def _generic_delete_test(self, urlpath, ent_type):
        global sample_keys
        encoded_key = sample_keys[ent_type]
        if len(encoded_key) > 0:
            url = BASE_URL + urlpath + encoded_key
            r = requests.delete(url)
            self.assertEqual(r.status_code, 204, "expected response code 204, got " + str(r.status_code))

            time.sleep(3)
            r = requests.get(BASE_URL + urlpath)
            list_of_dicts = r.json()
            keys = [x['encoded_key'] for x in list_of_dicts]
            self.assertNotIn(encoded_key, keys, "entity was not deleted")
            sample_keys[ent_type] = ""
        else:
            self.fail("no saved entity key from last test")

    def _generic_post_put(self, urlpath, ent_type, new_entity, fun, parent=None):
        global sample_keys

        json_to_send = json.dumps(new_entity)
        print json_to_send
        r = fun(BASE_URL + urlpath, json_to_send)
        self.assertEqual(r.status_code, 201, "expected status code 201, got " + str(r.status_code))
        created_object = r.json()
        self.assertIsInstance(created_object, dict)
        if parent:
            self.assertIn('parent', created_object)
            self.assertEqual(created_object['parent'], parent, "parent set wrong or not at all")
            self.assertIn('parent_name', created_object, "parent_name not set")
            del created_object['parent']
            del created_object['parent_name']

        sample_keys[ent_type] = created_object['encoded_key']
        created_object.pop('encoded_key', None)
        created_object.pop('lat', None)
        created_object.pop('lng', None)
        self.assertDictEqual(new_entity, self._ununicode(created_object))

    @unittest.skipIf(fresh_dev_server, "no data to query yet")
    def test009_get_all_monsters(self):
        print "test_get_all_monsters: "
        self._generic_get_test(MONSTER_PATH, MONSTER_MODEL, MONSTER_MODEL_NULLABLE, 'monster')
        print "passed"

    @unittest.skipIf(fresh_dev_server, "no data to query yet")
    def test036_get_all_sightings(self):
        print "test_get_all_sightings: "
        self._generic_get_test(SIGHTING_PATH, SIGHTING_MODEL, SIGHTING_MODEL_NULLABLE, 'sighting')
        print "passed"

    @unittest.skipIf(fresh_dev_server, "no data to query yet")
    def test020_get_one_monster(self):
        print "test_get_one_monster: "
        self._generic_get_test(MONSTER_PATH, MONSTER_MODEL, MONSTER_MODEL_NULLABLE, 'monster', False)
        print "passed"

    @unittest.skipIf(fresh_dev_server, "no data to query yet")
    def test037_get_one_sighting(self):
        print "test_get_one_sighting: "
        self._generic_get_test(SIGHTING_PATH, SIGHTING_MODEL, SIGHTING_MODEL_NULLABLE, 'sighting', False)
        print "passed"

    @unittest.skipIf(fresh_dev_server, "no data to query yet")
    def test025_get_entities_with_bad_key(self):
        print "test_get_with_bogus_key"
        bogus_key = "awevdcvweroiohivnlkn"
        for p in [MONSTER_PATH, SIGHTING_PATH]:
            url = BASE_URL + p + bogus_key
            r = requests.get(url)
            self.assertEqual(r.status_code, 404)
        print "passed"

    #@unittest.skip("don't need any more monsters")
    def test031_create_monster(self):
        new_mon = {"description": "created by python unittest"}
        new_mon['name'] = random.choice(names) + random.choice(surnames)
        new_mon['image_url'] = "http://images.clipartpanda.com/monster-clip-art-three-eyed-monster.png"
        new_mon['created_by'] = None
        self._generic_post_put(MONSTER_PATH, 'monster', new_mon, requests.post)

    @unittest.skipIf(fresh_dev_server, "no data to query yet")
    def test032_create_sighting(self):
        mon_key = sample_keys['monster']
        if len(mon_key) > 0:
            urlpath = MONSTER_PATH + mon_key + SIGHTING_PATH
            lat = 45.635203 + (random.random() - .5) / 100
            lon = -122.612089 + (random.random() - .5) / 100
            loc_string = str(lat) + "," + str(lon)
            timestamp = str(datetime.datetime.now())
            new_sighting = {"timestamp": timestamp, "location": loc_string, "notes": "seen it", "sighted_by": None}
            self._generic_post_put(urlpath, 'sighting', new_sighting, requests.post, parent=mon_key)
        else:
            self.fail("no saved entity key from last test")

    @unittest.skipIf(fresh_dev_server, "no data to query yet")
    def test033_get_sightings_of_monster(self):
        print "test_get_sightings_of_monster"
        self._generic_get_test(MONSTER_PATH, SIGHTING_MODEL, SIGHTING_MODEL_NULLABLE, 'monster', multi=True, path_postfix=SIGHTING_PATH)
        print "passed"

    @unittest.skipIf(fresh_dev_server, "no data to query yet")
    def _generic_update_test(self, entity_type, key_to_change, urlpath, model, nullable):
        test_key = sample_keys[entity_type]
        if len(test_key) > 0:
            url = BASE_URL + urlpath + test_key
            old_ent = requests.get(url).json()
            self.assertIsInstance(old_ent, dict, "expected a dict to be returned, instead got " + str(old_ent))
            self._check_dict_format(old_ent, model, nullable)

            old_ent[key_to_change] = "changed this field..."

            json_to_put = json.dumps(self._ununicode(old_ent))
            r = requests.put(url, json_to_put)
            self.assertEqual(r.status_code, 204, "expected status code 204, got " + str(r.status_code))

            #time.sleep(5)
            new_ent = requests.get(url).json()
            self.assertIsInstance(new_ent, dict)
            self.assertDictEqual(old_ent, new_ent, "changes were not saved to the datastore")
        else:
            self.fail("no saved entity key from last test")


    @unittest.skipIf(skip_extra_tests, "no time for this")
    def test035_query_by_location(self):
        """
            1. create a sighting for a monster at a location with a unique note
            2. determine ne and sw points for the location by subtracting and adding a small ammount
            3. query based on those points
            4. check to see if the created sighting is in the results
            5. delete the sighting
        """
        print "test_query_by_location: "
        mon_key = sample_keys['monster']
        if len(mon_key) > 0:
            urlpath = MONSTER_PATH + mon_key + SIGHTING_PATH
            loc_string = "44.5672,-123.2786"
            timestamp = str(datetime.datetime.now())
            new_sighting = {"timestamp": timestamp, "location": loc_string, "notes": "query by loc", "sighted_by": None}
            r = requests.post(BASE_URL + urlpath, json.dumps(new_sighting))
            if r.status_code == 201:
                created_sighting = r.json()
                ne = "44.57,-123.27"
                sw = "44.56,-123.3"
                query_str = "?ne=" + ne + "&sw=" + sw
                time.sleep(3)
                r = requests.get(BASE_URL + SIGHTING_PATH + query_str)
                self.assertEqual(r.status_code, 200, "status code " + str(r.status_code) + " returned")
                query_results = r.json()
                self.assertGreater(len(query_results), 0, "no results from query (should have been at least one)")
                key = created_sighting['encoded_key']
                result_keys = [x['encoded_key'] for x in query_results]
                self.assertIn(key, result_keys, "test sighting not in results")
                time.sleep(3)
                r = requests.delete(BASE_URL + SIGHTING_PATH + key)
                self.assertEqual(r.status_code, 204, "couldn't delete test sighting")
            else:
                self.fail("couldn't create test sighting")
        else:
            self.fail("no saved entity key from last test")
        print "passed"

    @unittest.skipIf(skip_extra_tests, "no time for this")
    def test040_update_monster(self):
        print "test_update_monster: "
        self._generic_update_test('monster', 'description', MONSTER_PATH, MONSTER_MODEL, MONSTER_MODEL_NULLABLE)
        print "passed"

    @unittest.skipIf(skip_extra_tests, "no time for this")
    def test045_update_sighting(self):
        print "test_update_sighting: "
        self._generic_update_test('sighting', 'notes', SIGHTING_PATH, SIGHTING_MODEL, SIGHTING_MODEL_NULLABLE)
        print "passed"

    @unittest.skipIf(accumulating, "accumulating entities")
    def test050_delete_sighting(self):
        print "test_delete_sighting: "
        self._generic_delete_test(SIGHTING_PATH, 'sighting')
        print "passed"

    @unittest.skipIf(accumulating, "accumulating entities")
    def test060_delete_monster(self):
        print "test_delete_monster: "
        self._generic_delete_test(MONSTER_PATH, 'monster')
        print "passed"


if __name__ == '__main__':
    print """
    Peter Lindberg, CS496 w15, Assignment 3: part 2
    Monspotting REST api tests

    There are 13 tests.  Some take a few seconds.  
    On my computer the whole test suite takes about 16 seconds to run.

    """
    unittest.main(verbosity=2)