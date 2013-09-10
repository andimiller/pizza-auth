import ts3tools, announce
from ldaptools import LDAPTools
from keytools import KeyTools
import json
from ldap import MOD_ADD, MOD_DELETE, MOD_REPLACE

# Load configuration
with open("config.json") as fh:
	config=json.loads(fh.read())
assert(config)

# Set up all classes
ldaptools = LDAPTools(config)
keytools = KeyTools(config)

safecharacters = ["twistedbot", "pingbot", "webchat", "deszra", "dimethus"]

if __name__ == "__main__":
	for character in ldaptools.getusers("objectclass=xxPilot"):
		try:
			characters = keytools.getcharacters(character.keyID, character.vCode)
			characters = json.dumps(characters, default=lambda x:x.__dict__)
			characters = json.loads(characters)
			results = {}
			for char in characters:
				r = {}
				for col, row in zip(char["_cols"], char["_row"]):
					r[col] = row
				r["result"] = char["result"]
				r["allianceName"] = char["allianceName"]
				r["allianceID"] = char["allianceID"]
				results[r["name"]] = r
			assert(character.characterName[0] in results)
			newcharacter = results[character.characterName[0]]
			if character.accountStatus[0] != newcharacter["result"]:
				print character.get_id(), "status update!"
				print "\t", character.accountStatus[0], "->", newcharacter["result"]
				ldaptools.modattr(character.get_id(), MOD_REPLACE, "accountStatus", newcharacter["result"])

			create = False
			if not hasattr(character, "alliance"):
				create = True
				character.alliance = [""]
			if character.alliance[0] != newcharacter["allianceName"]:
				print character.get_id(), "alliance update!"
				print "\t", character.alliance[0], "->", newcharacter["allianceName"]
				if create:
					ldaptools.modattr(character.get_id(), MOD_ADD, "alliance", newcharacter["allianceName"])
				else:
					ldaptools.modattr(character.get_id(), MOD_REPLACE, "alliance", newcharacter["allianceName"])
			if character.corporation[0] != newcharacter["corporationName"]:
				print character.get_id(), "corp update!"
				print "\t", character.corporation[0], "->", newcharacter["corporationName"]
				ldaptools.modattr(character.get_id(), MOD_REPLACE, "corporation", newcharacter["corporationName"])

		except RuntimeError:
			if character.get_id() not in safecharacters:
				print "API key no longer valid, requesting deletion of", character.get_id(), character.corporation[0]
				print ldaptools.deleteuser(character.get_id())

