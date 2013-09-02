import ts3

class ts3manager():
	def __init__(self, config):
		self.config = config["ts3"]

	def modpermissions(self, uid, remove=False, groupid=None):
		if groupid==None:
			groupid = self.config["servergroups"]["full"]
		server = ts3.TS3Server(str(self.config["server"]), self.config["port"])
		server.login(str(self.config["user"]), str(self.config["password"]))
		server.use(1)
		response = server.send_command('clientgetnamefromuid', {'cluid':uid})
		if (response.data)[0] == {'': None}:
			return (False, "User not found in TS3 database")
		dbid = response.data[0]['cldbid']
		groups = server.send_command('servergroupsbyclientid', {'cldbid':dbid})
		print groups.data[0]
		sgid = groups.data[0]['sgid']
		if not remove:
			response = server.send_command('servergroupaddclient', {'sgid':int(groupid), 'cldbid':dbid})
		else:
			response = server.send_command('servergroupdelclient', {'sgid':int(groupid), 'cldbid':dbid})
		print response
		server.disconnect()
		return (True, "Permissions applied")
