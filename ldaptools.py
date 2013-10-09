#!/usr/bin/env python
import ldap
import ldap.modlist as modlist
import subprocess

from flask.ext.login import UserMixin

class ServerDownException(Exception): pass

class User(UserMixin):

	def __init__(self, attr, domain):
		self.__dict__.update(attr)
		self.domain = domain

	def get_id(self):
		return self.uid[0]

	def get_authgroups(self):
		if not hasattr(self, "authGroup"):
			return []
		else:
			return filter(lambda x:not x.endswith("-pending"), self.authGroup)

	def get_pending_authgroups(self):
		if not hasattr(self, "authGroup"):
			return []
		else:
			results = filter(lambda x:x.endswith("-pending"), self.authGroup)
			return map(lambda x:x[:-8], results)

	def get_jid(self):
		domains = {
			"OI": self.domain,
			"PIZZA": self.domain,
			"Ally": "allies." + self.domain,
			"Ineligible": "public." + self.domain
		}
		return "%s@%s" % (self.uid[0], domains[self.accountStatus[0]])

	def get_ts3ids(self):
		if hasattr(self, "ts3uid"):
			return self.ts3uid
		else:
			return []

class LDAPTools():
	def __init__(self, config):
		self.authconfig = config
		self.config = config["ldap"]

	def makeSecret(self, password):
		return subprocess.check_output(["slappasswd","-h","{SSHA}","-s", password]).rstrip("\n")

	def adduser(self, attrs):
		l = ldap.initialize(self.config["server"])
		l.simple_bind(self.config["admin"], self.config["password"])
		dn = "uid=%s,%s" % (attrs["uid"], self.config["memberdn"])
		attrs["objectClass"] = ['top', 'account', 'simpleSecurityObject', 'xxPilot']
		attrs["userPassword"] = self.makeSecret(attrs["userPassword"])
		ldif = modlist.addModlist(attrs)
		l.add_s(dn, ldif)
		l.unbind_s()

	def modts3id(self, uid, change, ts3id):
		l = ldap.initialize(self.config["server"])
		l.simple_bind(self.config["admin"], self.config["password"])
		dn = "uid=%s,%s" % (uid, self.config["memberdn"])
		l.modify_s(dn, [(change, 'ts3uid', ts3id)])
		l.unbind_s()
		return True

	def modattr(self, uid, change, attr, value):
		l = ldap.initialize(self.config["server"])
		l.simple_bind(self.config["admin"], self.config["password"])
		dn = "uid=%s,%s" % (uid, self.config["memberdn"])
		l.modify_s(dn, [(change, str(attr), str(value))])
		l.unbind_s()
		return True

	def deleteuser(self, uid):
		l = ldap.initialize(self.config["server"])
		l.simple_bind(self.config["admin"], self.config["password"])
		dn = "uid=%s,%s" % (uid, self.config["memberdn"])
		l.delete_s(dn)
		l.unbind_s()
		return True

	def modgroup(self, uid, change, group):
		l = ldap.initialize(self.config["server"])
		l.simple_bind(self.config["admin"], self.config["password"])
		dn = "uid=%s,%s" % (uid, self.config["memberdn"])
		l.modify_s(dn, [(change, 'authGroup', group)])
		l.unbind_s()
		return True

	def updateuser(self, uid, modattrs):
		l = ldap.initialize(self.config["server"])
		l.simple_bind(self.config["admin"], self.config["password"])
		dn = "uid=%s,%s" % (uid, self.config["memberdn"])
		ldap_filter = "uid="+uid
		result_id = l.search(self.config["memberdn"], ldap.SCOPE_SUBTREE, ldap_filter, None)
		if result_id:
			type, data = l.result(result_id, 0)
		if data:
			dn, attrs = data[0]
			oldattrs = attrs
			newattrs = attrs.copy()
			newattrs.update(modattrs)
			# now change it
			newattrs.update(oldattrs)
			ldif = modlist.modifyModlist(oldattrs, newattrs)
			print ldif
			l.modify_s(dn, ldif)
			l.unbind_s()
			return True
		else:
			return False

	def getuser(self, id):
		if not isinstance(id, basestring):
			id = id[0]
		l = ldap.initialize(self.config["server"])
		l.simple_bind(self.config["admin"], self.config["password"])
		ldap_filter = "uid="+id
		result_id = l.search(self.config["memberdn"], ldap.SCOPE_SUBTREE, ldap_filter, None)
		if result_id:
			type, data = l.result(result_id, 0)
		if data:
			dn, attrs = data[0]
			l.unbind_s()
			return User(attrs, self.authconfig["auth"]["domain"])
		l.unbind_s()
		return None

	def check_credentials(self, username, password):
		try:
			ldap_client = ldap.initialize(self.config["server"])
			ldap_client.set_option(ldap.OPT_REFERRALS,0)
			ldap_client.simple_bind_s("uid=%s,%s" % (username, self.config["memberdn"]), password)
		except ldap.INVALID_DN_SYNTAX:
			ldap_client.unbind()
			return False
		except ldap.INVALID_CREDENTIALS:
			ldap_client.unbind()
			return False
		except ldap.UNWILLING_TO_PERFORM:
			ldap_client.unbind()
			return False
		except ldap.SERVER_DOWN:
			ldap_client.unbind()
			raise ServerDownException()
			return False
		ldap_client.unbind()
	  	return True

	def getusers(self, searchfilter):
		l = ldap.initialize(self.config["server"])
		l.simple_bind(self.config["admin"], self.config["password"])
		ldap_filter = searchfilter
		result_id = l.search(self.config["memberdn"], ldap.SCOPE_SUBTREE, ldap_filter, None)
		results = []
		while 1:
			result_type, result_data = l.result(result_id, 0)
			if (result_data == []):
				break
			else:
				if result_type == ldap.RES_SEARCH_ENTRY:
					results.append(result_data[0][1])
		return map(lambda x:User(x, self.authconfig["auth"]["domain"]), results)


