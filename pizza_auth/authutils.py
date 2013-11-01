from flask import current_app, redirect, flash, request, abort
from flask.ext.login import current_user
from functools import wraps


def groups_required(filter_function):
	def real_decorator(func):
		"Decorates a function to require a certain auth group to continue"
		@wraps(func)
		def decorated_view(*args, **kwargs):
			if len(filter(filter_function, current_user.authGroup))==0:
				flash("You must be in one of the correct groups to access that.", "danger")
				return redirect("/")
			else:
				return func(*args, **kwargs)
		return decorated_view
	return real_decorator

def group_required(group):
	def real_decorator(func):
		"Decorates a function to require a certain auth group to continue"
		@wraps(func)
		def decorated_view(*args, **kwargs):
			if group not in current_user.authGroup:
				flash("You must be in the %s group to access that." % group, "danger")
				return redirect("/")
			else:
				return func(*args, **kwargs)
		return decorated_view
	return real_decorator

def api_key_required(func):
	@wraps(func)
	def decorated_view(*args, **kwargs):
		key = request.args.get('key','')
		if key not in current_app.config["apikeys"]:
			abort(401)
		else:
			return func(*args, **kwargs)
	return decorated_view
