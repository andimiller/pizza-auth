from flask import current_app, redirect, flash
from flask.ext.login import current_user
from functools import wraps

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

