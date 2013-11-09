from flask import current_app, redirect, flash, request, abort
from flask.ext.login import current_user
from ast import literal_eval
from urllib import quote
import hashlib, redis_wrap

operationshash = redis_wrap.get_hash('operations')
mumblehash = redis_wrap.get_hash('mumble')

def generate_user(op_hash, character_name, **kwargs):
	if op_hash in operationshash:
		tmpophash = literal_eval(operationshash[op_hash])
		m = hashlib.md5()
		m.update(character_name)
		username = "user_%s" % (m.hexdigest(),)
		m = hashlib.md5()
		m.update(op_hash)
		m.update(character_name)
		userdata = {
				'username': username,
				'password': m.hexdigest(),
				'op_hash': op_hash,
				'display_name': character_name
			}
		userdata.update(kwargs)
		mumblehash[username] = userdata
		return userdata
	return None

def generate_op(op_name, **kwargs):
	m = hashlib.md5()
	m.update(op_name)
	ophash = m.hexdigest()
	if ophash not in operationshash:
		opdata = {
				'op_name': op_name,
				'op_fc': 'Fleet Commander X',
				'op_channel': "/Ops/%s" % (quote(op_name),)
				}
		opdata.update(kwargs)
		operationshash[ophash] = opdata
		return ophash
	else:
		return ophash

	return None

def confirm_op(op_hash):
	return op_hash in operationshash

def confirm_user(username):
	return username in mumblehash

def destroy_user(username):
	if confirm_user(username):
		del(mumblehash[username])

def destroy_op(op_hash):
	if confirm_op(op_hash):
		operation = literal_eval(operationshash[op_hash])
		for username in mumblehash.keys():
			tmp_dict = literal_eval(mumblehash[username])
			if 'op_hash' in tmp_dict:
				if tmp_dict['op_hash'] == op_hash:
					destroy_user(username)

		del(operationshash[op_hash])
		return True

	return False
