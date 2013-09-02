import xmpp
from ldaptools import LDAPTools
class pingbot():
	def __init__(self, config):
		self.config = config["pingbot"]
		self.username = self.config["username"]
		self.passwd = self.config["passwd"]
		self.domain = self.config["domain"]
		self.ldaptools = LDAPTools(config)

	def sendannounce(self, server, message):
		tojid = server+"/announce/online"
		jidparams={}
		jidparams['jid'] = self.username+"@"+server
		jidparams['password'] = self.passwd

		jid=xmpp.protocol.JID(jidparams['jid'])
		cl=xmpp.Client(jid.getDomain(), debug=[])

		con=cl.connect()
		if not con:
		    print 'could not connect!'
		    sys.exit()
		print 'connected with',con
		auth=cl.auth(jid.getNode(),jidparams['password'],resource=jid.getResource())
		if not auth:
		    print 'could not authenticate!'
		    sys.exit()
		print 'authenticated using',auth

		id=cl.send(xmpp.protocol.Message(tojid,message))
		print 'sent message with id',id

	def generatemessage(self, sender, to, message):
		result = message
		result = result+"\n\n"
		result = result+"== broadcast from %s to %s ==" % (sender, to)
		return result

	def broadcast(self, sender, to, message, servers):
		for server in servers:
			self.sendannounce(server, self.generatemessage(sender, to, message))

	def sendmessage(self, tojids, message):
		jidparams={}
		jidparams['jid'] = self.username+"@"+self.domain
		jidparams['password'] = self.passwd

		jid=xmpp.protocol.JID(jidparams['jid'])
		cl=xmpp.Client(jid.getDomain(), debug=[])

		con=cl.connect()
		if not con:
		    print 'could not connect!'
		    sys.exit()
		print 'connected with',con
		auth=cl.auth(jid.getNode(),jidparams['password'],resource=jid.getResource())
		if not auth:
		    print 'could not authenticate!'
		    sys.exit()
		print 'authenticated using',auth
		total = 0
		for tojid in tojids:
			id=cl.send(xmpp.protocol.Message(tojid,message))
			total = total+1
		cl.disconnect()
		return total

	def groupbroadcast(self, sender, ldapfilter, message, to):
		message = self.generatemessage(sender, to, message)
		users = self.ldaptools.getusers(ldapfilter)
		tojids = map(lambda x:x.get_jid(), users)
		return self.sendmessage(tojids, message)

