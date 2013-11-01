#!/usr/bin/env python

import MySQLdb
import urllib
import re
import pygments.console
from BeautifulSoup import BeautifulStoneSoup
from ldaptools import LDAPTools
import json

# Load configuration
with open("config.json") as fh:
	config=json.loads(fh.read())
assert(config)

# Set up all classes

skillstripper = re.compile('.*typeid="(\d+)".* level="(\d)".*')

class SkillIndexer():
	def __init__(self, config):
		self.ldaptools = LDAPTools(config)
		self.config = config["skillindexer"]
		self.authconfig = config

	def getSkills(self, db, name, id, vCode):
		accountCharacters = "http://api.eveonline.com/account/Characters.xml.aspx"
		charSheet = "http://api.eveonline.com/char/CharacterSheet.xml.aspx"

		print "Processing %s" % name
		params = urllib.urlencode({"keyID": id, "vCode": vCode})
		f = urllib.urlopen(accountCharacters+"?"+params)
		data = f.read()
		f.close()
		soup = BeautifulStoneSoup(data)
		r = soup.findAll("row", {"name":unicode(name)})
		if len(r)==0:
			return (1, "Character not found")
		corp = r[0]["corporationname"]
		charid = r[0]["characterid"]
		params = urllib.urlencode({"keyID": id, "vCode": vCode, "characterID":charid})
		f = urllib.urlopen(charSheet+"?"+params)
		data = f.read()
		f.close()
		soup = BeautifulStoneSoup(data)
		error = soup.findAll("error")
		if len(error):
			print "Error"

		skills = str(soup.findAll("rowset", {"name": "skills"})[0]).split("\n")
		skills = map(lambda x:x.replace("</row>", ""), skills)
		skills = filter(lambda x:x.startswith("<row "), skills)
		skills = map(lambda x: skillstripper.match(x).groups(), skills)
		print len(skills)
		for t, l in skills:
			t=int(t)
			l=int(l)
			r = db.execute('INSERT INTO skills (name, typeid, level) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE level=%s', (name, t, l, l) )


	def main(self):
		#ldap
		everyone = self.ldaptools.getusers("alliance=" + self.authconfig["auth"]["alliance"])

		#database server
		db = MySQLdb.connect(self.config["server"], self.config["user"], self.config["password"], self.config["database"])
		c = db.cursor()
		c.execute('truncate skills;')
		for user in everyone:
			try:
				self.getSkills(c, user.characterName[0], user.keyID[0], user.vCode[0])
			except Exception as e:
				print e
		db.commit()

if __name__ == "__main__":
	s = SkillIndexer(config)
	s.main()
