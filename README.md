# PIZZA Auth

LDAP-Backed Services Auth System for EVE Online

## Requirements

Please install the following with pip:

* Flask
* Flask-Login
* Requests
* python-ldap

Optional:
* ts3 package from https://github.com/nikdoof/python-ts3

## Configuration

Configuration is done via a config.json file in the web application's root folder, here's a sample one:

```
{
	"pingbot": {
		"username": "pingbot",
		"passwd": "",
		"domain": ""
	},

	"keytools": {
		"executorkeyid": "",
		"executorkeyvcode": "",
		"alliancelimit": 4.9
	},

	"groups": {
		"closedgroups": [
			"admin",
			"ping",
			"capital"
		],
		"opengroups": [
			"dota",
			"social",
		],
		"publicgroups": [
			"dota"
		]
	},
	"ts3": {
		"user": "serveradmin",
		"password": "",
		"server": "",
		"port": 10011,
		"servergroups":	{
			"full": "1",
			"ally": "2",
			"none": "3"
		}
	},

	"ldap": {
		"server": "ldap://localhost/",
		"admin": "cn=admin,dc=yoursite,dc=com",
		"password": "",
		"basedn": "dc=yoursite,dc=com",
		"memberdn": "ou=People,dc=yoursite,dc=com"
	},

	"skillindexer": {
		"server": "localhost",
		"user": "authuser",
		"password": "",
		"database": "auth"
	}

}
```

## Installation

### LDAP

This software is intended to be used with OpenLDAP, along with it's standard schemas, there is one extra schema included in the schema directory called pizza.schema.

You can insert this into an ou=config setup like so:

Create a schema_convert.conf with contents like this
```
include /etc/ldap/schema/core.schema
include /etc/ldap/schema/collective.schema
include /etc/ldap/schema/corba.schema
include /etc/ldap/schema/cosine.schema
include /etc/ldap/schema/duaconf.schema
include /etc/ldap/schema/dyngroup.schema
include /etc/ldap/schema/inetorgperson.schema
include /etc/ldap/schema/java.schema
include /etc/ldap/schema/misc.schema
include /etc/ldap/schema/nis.schema
include /etc/ldap/schema/openldap.schema
include /etc/ldap/schema/ppolicy.schema
include /etc/ldap/schema/pizza.schema
```

Make a folder to put converted schemas into
```
mkdir /tmp/ldif_output
```

Run the conversion
```
slaptest -f schema_convert.conf -F /tmp/ldif_output
```

edit the {xx}pizza.ldif file and rename it so the dn/cn look like this
```
dn: cn=pizza,cn=schema,cn=config
cn: pizza
```

And remove the extra lines that look like this from the end:
```
structuralObjectClass: olcSchemaConfig
entryUUID: 65f628a4-aa72-1032-9bfb-3d59b251971c
creatorsName: cn=config
createTimestamp: 20130905122822Z
entryCSN: 20130905122822.411617Z#000000#000#000000
modifiersName: cn=config
modifyTimestamp: 20130905122822Z
```

Insert the new schema
```
ldapadd -Q -Y EXTERNAL -H ldapi:/// -f /tmp/ldif_output/cn=config/cn=schema/cn=\{xx\}pizza.ldif
```

### Deploying under uwsgi

To deploy the application as a wsgi container you can use the following uwsgi settings. These may be adapted for other wsgi-capable application servers.

```
[uwsgi]
socket = /var/run/auth.sock
chmod-socket = 666
processes = 4
master = true
chdir = /opt/pizza-auth
pp = /opt/pizza-auth
module = main
callable = app
```

This can be served using an nginx site configuration like the following:

```
server {
        server_name auth.yourdomain.net;

        root /var/www/;

        location / {
                include         uwsgi_params;
                uwsgi_pass      unix:/var/run/auth.sock;
        }
}
```
