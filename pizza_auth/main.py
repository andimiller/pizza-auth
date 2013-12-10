import json
from flask import Flask, flash, session, render_template, redirect, request, abort, url_for, escape
from flask.ext.login import LoginManager, login_user, logout_user, login_required, current_user
import ts3tools, announce
from ldaptools import LDAPTools
from keytools import KeyTools
from emailtools import EmailTools
from reddittools import RedditTools
from authutils import groups_required, group_required, api_key_required
from collections import namedtuple
from ldap import ALREADY_EXISTS
from ldap import MOD_ADD, MOD_DELETE, MOD_REPLACE
import string, random
import redis_wrap
from updateaccounts import update_characters

app = Flask(__name__)

# Load configuration
with open("config.json") as fh:
	config=json.loads(fh.read())
assert(config)
app.config.update(config)

# Set up all classes
login_manager = LoginManager()
login_manager.init_app(app)
pingbot = announce.pingbot(app.config)
ts3manager = ts3tools.ts3manager(app.config)
ldaptools = LDAPTools(app.config)
keytools = KeyTools(app.config)
emailtools = EmailTools(app.config, app.jinja_loader)

if "reddit" in app.config:
	reddittools = RedditTools(app.config,ldaptools)
else:
	reddittools = None

@login_manager.user_loader
def load_user(userid):
	return ldaptools.getuser(userid)

@app.route("/login", methods=["POST", "GET"])
def login():
	if request.method=="GET":
		return render_template("login.html", next_page=request.args.get("next"))
	username = request.form["username"]
	password = request.form["password"]
	next_page = request.form["next_page"]
	if ldaptools.check_credentials(username, password):
		user = ldaptools.getuser(username)
		login_user(user)
		flash("Logged in as %s" % username, "success")
		if next_page and next_page!="None":
			return redirect(next_page)
		else:
			return redirect("/")
	else:
		flash("Invalid Credentials. ", "danger")
		return redirect("/login")
login_manager.login_view = "/login"

recoverymap = redis_wrap.get_hash("recovery")

@app.route("/forgot_password", methods=["POST", "GET"])
def forgot_password():
	if request.method=="GET":
		return render_template("forgot_password.html")
	username = request.form["username"]
	email = request.form["email"]
	try:
		user = ldaptools.getuser(username)
		assert(user)
		assert(email == user.email[0])
		token = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(24))
		url = request.host_url+"recovery/"+token
		recoverymap[token] = username
		emailtools.render_email(email, "Password Recovery", "forgot_password.txt", url=url, config=app.config)
		flash("Email sent to "+email, "success")
	except Exception as e:
		flash("Username/Email mismatch", "danger")
	return redirect("/login")

@app.route("/recovery/<token>")
def recovery(token):
	if token not in recoverymap:
		flash("Recovery Token Expired", "danger")
		return redirect("/login")
	else:
		user = ldaptools.getuser(recoverymap[token])
		login_user(user)
		del recoverymap[token]
		flash("Logged in as %s using recovery token." % user.get_id(), "success")
		return render_template("account_reset.html")

@app.route("/logout")
@login_required
def logout():
	logout_user()
	return redirect("/")

@app.route("/account")
@login_required
def account():
	reddit_flag = "reddit" in app.config
	return render_template("account.html", reddit_flag=reddit_flag)

@app.route("/account/update", methods=['POST'])
@login_required
def update_account():
	email = request.form["email"]
	oldpassword = request.form["oldpassword"]
	api_id = request.form["api_id"]
	api_key = request.form["api_key"]
	update_needed = False
	if api_id != current_user.keyID[0] or api_key != current_user.vCode[0]:
		update_needed = True
	if not ldaptools.check_credentials(current_user.get_id(), oldpassword):
		flash("You must confirm your old password to update your account.", "danger")
		return redirect("/account")
	try:
		if all(x in request.form for x in ["password", "password_confirm", "oldpassword"]):
			if request.form["password"] != request.form["password_confirm"]:
				flash("Password confirmation mismatch.", "danger")
				return redirect("/account")
			result = ldaptools.modattr(current_user.get_id(), MOD_REPLACE, "userPassword", ldaptools.makeSecret(request.form["password"]))
			assert(result)
		result = ldaptools.modattr(current_user.get_id(), MOD_REPLACE, "email", email)
		assert(result)
		result = ldaptools.modattr(current_user.get_id(), MOD_REPLACE, "keyID", api_id)
		assert(result)
		result = ldaptools.modattr(current_user.get_id(), MOD_REPLACE, "vCode", api_key)
		assert(result)
		flash("Account updated", "success")
	except Exception:
		flash("Update failed", "danger")
	if update_needed is True:
		update_characters([current_user.get_id()])
	app.logger.info('User account {0} infos changed'.format(current_user.get_id()))
	return redirect("/account")

@app.route("/groups")
@login_required
def groups():
	yourgroups = current_user.get_authgroups() + current_user.get_pending_authgroups()
	notyours = lambda x: x not in yourgroups
	if "Ineligible" in current_user.accountStatus:
		return render_template("groups.html", closed_groups=filter(notyours, []), open_groups=filter(notyours, app.config["groups"]["publicgroups"]))
	else:
		return render_template("groups.html", closed_groups=filter(notyours, app.config["groups"]["closedgroups"]), open_groups=filter(notyours, app.config["groups"]["opengroups"]))


@app.route("/admin", methods=["GET", "POST"])
@login_required
@group_required("admin")
def admin():
	user = None
	if "userid" in request.args:
		user = ldaptools.getuser(request.args["userid"])
		if not user:
			flash("Cannot find that user", "danger")
		else:
			user = user.__dict__
	return render_template("admintools.html", user=user)

@app.route("/admin/deleteuser", methods=["POST"])
@login_required
@group_required("admin")
def deleteuser():
	user = request.form["userid"]
	ldaptools.deleteuser(user)
	flash("Successful delete for %s" % user, "success")
	return redirect("/admin")

@app.route("/admin/updateuser", methods=["POST"])
@login_required
@group_required("admin")
def updateuser():
	user = request.form["userid"]
	update_characters([user])
	flash("Successful update for %s" % user, "success")
	return redirect("/admin")

@app.route("/groups/admin")
@login_required
@groups_required(lambda x:x.startswith("admin"))
def groupadmin():
	if "admin" in current_user.authGroup:
		groups = groups=app.config["groups"]["closedgroups"]+app.config["groups"]["opengroups"]
	else:
		groups = map(lambda x:x[6:], filter(lambda x:x.startswith("admin-"), current_user.authGroup))
	pendingusers = ldaptools.getusers("authGroup=*-pending")
	applications = []
	for user in pendingusers:
		for group in user.get_pending_authgroups():
			if group in groups:
				applications.append((user.get_id(), group))
	return render_template("groupsadmin.html", applications=applications, groups=groups)

@app.route("/groups/list/<group>")
@login_required
@groups_required(lambda x:x.startswith("admin"))
def grouplist(group):
	users = ldaptools.getusers("authGroup="+group)
	return render_template("groupmembers.html", group=group, members=users)


@app.route("/groups/admin/approve/<id>/<group>")
@login_required
@groups_required(lambda x:x.startswith("admin"))
def groupapprove(id, group):
	if ("admin" not in current_user.get_authgroups()) and ("admin-%s" % group not in current_user.get_authgroups()):
		flash("You do not have the right to do that.", "danger")
		return redirect("/groups/admin")
	try:
		id = str(id)
		group = str(group)
		ldaptools.modgroup(id, MOD_DELETE, group+"-pending")
		ldaptools.modgroup(id, MOD_ADD, group)
		flash("Membership of %s approved for %s" % (group, id), "success")
		return redirect("/groups/admin")
	except:
		flash("Membership application not found", "danger")
		return redirect("/groups/admin")

@app.route("/groups/admin/deny/<id>/<group>")
@login_required
@groups_required(lambda x:x.startswith("admin"))
def groupdeny(id, group):
	if ("admin" not in current_user.get_authgroups()) and ("admin-%s" % group not in current_user.get_authgroups()):
		flash("You do not have the right to do that.", "danger")
		return redirect("/groups/admin")
	try:
		id = str(id)
		group = str(group)
		ldaptools.modgroup(id, MOD_DELETE, group+"-pending")
		flash("Membership of %s denied for %s" % (group, id), "success")
		return redirect("/groups/admin")
	except:
		flash("Membership application not found", "danger")
		return redirect("/groups/admin")

@app.route("/groups/admin/remove/<id>/<group>")
@login_required
@groups_required(lambda x:x.startswith("admin"))
def groupremove(id, group):
	if ("admin" not in current_user.get_authgroups()) and ("admin-%s" % group not in current_user.get_authgroups()):
		flash("You do not have the right to do that.", "danger")
		return redirect("/groups/admin")
	id = str(id)
	group = str(group)
	ldaptools.modgroup(id, MOD_DELETE, group)
	flash("Membership of %s removed for %s" % (group, id), "success")
	return redirect("/groups/list/"+group)


@app.route("/groups/admin/admin/<id>/<group>")
@login_required
@groups_required(lambda x:x.startswith("admin"))
def groupmkadmin(id, group):
	if ("admin" not in current_user.get_authgroups()) and ("admin-%s" % group not in current_user.get_authgroups()):
		flash("You do not have the right to do that.", "danger")
		return redirect("/groups/admin")
	id = str(id)
	group = str(group)
	try:
		ldaptools.modgroup(id, MOD_ADD, "admin-%s" % group)
		flash("Membership of admin-%s added for %s" % (group, id), "success")
	except:
		flash("That user is already in that group.", "danger")
	return redirect("/groups/list/"+group)

@app.route("/groups/admin/ping/<id>/<group>")
@login_required
@groups_required(lambda x:x.startswith("admin"))
def groupmkping(id, group):
	if ("admin" not in current_user.get_authgroups()) and ("admin-%s" % group not in current_user.get_authgroups()):
		flash("You do not have the right to do that.", "danger")
		return redirect("/groups/admin")
	id = str(id)
	group = str(group)
	try:
		ldaptools.modgroup(id, MOD_ADD, "ping-%s" % group)
		flash("Membership of ping-%s added for %s" % (group, id), "success")
	except:
		flash("That user is already in that group.", "danger")
	return redirect("/groups/list/"+group)





@app.route("/groups/apply/<group>")
@login_required
def group_apply(group):
	originalgroup = group
	group = str(group)
	assert(group in app.config["groups"]["closedgroups"]+app.config["groups"]["opengroups"])
	join = True
	if group in app.config["groups"]["closedgroups"]:
		group = group+"-pending"
		join = False
	if current_user.accountStatus[0]=="Ineligible":
		if group not in app.config["groups"]["publicgroups"]:
			flash("You cannot join that group.", "danger")
			return redirect("/groups")
	ldaptools.modgroup(current_user.get_id() , MOD_ADD, group)
	if join:
		flash("Joined %s group" % group, "success")
	else:
		flash("Applied for %s group" % originalgroup, "success")
	return redirect("/groups")

@app.route("/groups/remove/<group>")
@login_required
def group_remove(group):
	group = str(group)
	ldaptools.modgroup(current_user.get_id() , MOD_DELETE, group)
	flash("Removed %s group" % group, "success")
	return redirect("/groups")

@app.route("/ping")
@login_required
@groups_required(lambda x:x.startswith("ping"))
def ping():
	return render_template("ping.html")

@app.route("/ping/send", methods=["POST"])
@login_required
@group_required("ping")
def ping_send():
	servers = map(lambda x:x + config["auth"]["domain"], ["allies.", "", "public."])
	servers = filter(lambda x:x in request.form, servers)
	pingbot.broadcast(current_user.get_id(),",".join(servers), request.form["message"], servers)
	flash("Broadcasts sent to: "+", ".join(servers), "success")
	return redirect("/ping")

@app.route("/ping/group", methods=["POST"])
@login_required
@groups_required(lambda x:x.startswith("ping"))
def ping_send_group():
	if ("ping" not in current_user.get_authgroups()) and ("ping-%s" % request.form["group"] not in current_user.get_authgroups()):
		flash("You do not have the right to do that.", "danger")
		return redirect("/ping")
	count = pingbot.groupbroadcast(current_user.get_id(), "(|(authGroup={0})(corporation={0})(alliance={0}))".format(request.form["group"]), request.form["message"], request.form["group"])
	flash("Broadcast sent to %d members in %s" % (count, request.form["group"]), "success")
	return redirect("/ping")

@app.route("/ping/advgroup", methods=["POST"])
@login_required
@group_required("ping")
def ping_send_advgroup():
	ldap_filter = "("+request.form["filter"]+")"
	message = request.form["message"]
	count = pingbot.groupbroadcast(current_user.get_id(), ldap_filter, message, ldap_filter)
	flash("Broadcast sent to %d members in %s" % (count, ldap_filter), "success")
	return redirect("/ping")

@app.route("/services")
@login_required
def services():
	return render_template("services.html")

@app.route("/services/ts3id", methods=['POST'])
@login_required
def add_tss3id():
	ts3id = str(request.form["ts3id"])
	ts3group = {
			"Internal": app.config["ts3"]["servergroups"]["full"],
			"Ally": app.config["ts3"]["servergroups"]["ally"],
			"Ineligible": app.config["ts3"]["servergroups"]["none"]
			}
	ldaptools.modts3id(current_user.get_id() , MOD_ADD, ts3id)
	result = ts3manager.modpermissions(ts3id, groupid=ts3group[current_user.accountStatus[0]])
	if result:
		flash("TS3 ID added and auth requested.", "success")
	else:
		flash("Something blew up.", "error")
	return redirect("/services")


@app.route("/services/ts3id/reload", methods=['GET'])
@login_required
def refresh_ts3id():
	ts3ids = current_user.ts3uid
	ts3group = {
			"Internal": app.config["ts3"]["servergroups"]["full"],
			"Ally": app.config["ts3"]["servergroups"]["ally"],
			"Ineligible": app.config["ts3"]["servergroups"]["none"]
			}
	results = []
	for ts3id in ts3ids:
		results.append(ts3manager.modpermissions(ts3id, groupid=ts3group[current_user.accountStatus[0]]))
	flash("Results:"+str(results), "info")
	return redirect("/services")



@app.route("/services/ts3id/delete/<path:id>")
@login_required
def delete_ts3id(id):
	id = str(id)
	ts3manager.modpermissions(id, remove=True, groupid=app.config["ts3"]["servergroups"]["full"])
	ts3manager.modpermissions(id, remove=True, groupid=app.config["ts3"]["servergroups"]["ally"])
	ldaptools.modts3id(current_user.get_id() , MOD_DELETE, id)
	return redirect("/services")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
	if request.method == 'POST':
		session["keyid"] = request.form["keyid"]
		session["vcode"] = request.form["vcode"]
		return redirect(url_for("character"))
	if request.method == 'GET':
		return render_template("signup.html", session=session)


@app.route('/')
def index():
	if current_user.is_anonymous():
		return render_template("index.html")
	else:
		return render_template("index_user.html")

@app.route('/character')
def character():
	try:
		keyid = session["keyid"]
		vcode = session["vcode"]
		chars = keytools.getcharacters(keyid, vcode)
		session["chars"] = json.dumps(chars, default=lambda x:x.__dict__)
		return render_template("characters.html", characters=chars)
	except Exception as e:
		flash("Invalid API key", "danger")
		return redirect(url_for("index"))

@app.route('/signup/<name>')
def pickcharactername(name):
	session["username"] = str(name).replace(" ", "_").lower()
	session["username"] = session["username"].replace("'", "")
	characters = json.loads(session["chars"])
	results = []
	for char in characters:
		r = {}
		for col, row in zip(char["_cols"], char["_row"]):
			r[col] = row
		r["result"] = char["result"]
		r["allianceName"] = char["allianceName"]
		r["allianceID"] = char["allianceID"]
		results.append(r)
	possiblecharacters = filter(lambda x: name in x.values(), results)
	if len(possiblecharacters)>0:
		character = possiblecharacters[0]
		session["characterName"] = character["name"]
		session["corporation"] = character["corporationName"]
		session["alliance"] = character["allianceName"]
		session["accountStatus"] = character["result"]
		return render_template("pickcharacter.html", character=character, session=session)
	else:
		abort(404)

@app.route('/create_account', methods=['POST'])
def create_account():
	attrs = {}
	attrs["email"] = request.form.get("email")
	attrs["userPassword"] = request.form.get("password")
	attrs["uid"] = session["username"]
	attrs["vCode"] = session["vcode"]
	attrs["keyID"] = session["keyid"]

	attrs["characterName"] = session["characterName"]
	attrs["corporation"] = session["corporation"]
	if "alliance" in session:
		attrs["alliance"] = session["alliance"]
	attrs["accountStatus"] = session["accountStatus"]

	for key in attrs:
		attrs[key] = str(attrs[key])

	try:
		ldaptools.adduser(attrs)
	except ALREADY_EXISTS:
		flash("User already exists", "danger")
		return redirect("/")

	user = ldaptools.getuser(attrs["uid"])
	login_user(user)
	flash("Created and logged in as %s" % attrs["uid"], "success")

	return redirect("/")

@app.route("/ping/complete")
def pingcomplete():
	allusers = ldaptools.getusers("objectClass=xxPilot")
	entities = []
	for user in allusers:
		if user.corporation[0] not in entities:
			entities.append(user.corporation[0])
		if hasattr(user, "alliance"):
			if user.alliance[0] not in entities:
				entities.append(user.alliance[0])
	term = request.args.get('term')
	results = filter(lambda x:x.lower().startswith(term.lower()), entities+app.config["groups"]["closedgroups"]+app.config["groups"]["opengroups"])
	return json.dumps(results)

@app.route("/account/reddit")
@login_required
def reddit():
	redirect_uri = app.config["reddit"]["redirect_base"] + url_for('reddit_loop')
	if hasattr(current_user, "redditAccount"):
		flash("Already registered with reddit: %s" % (current_user.redditName), "error")
		return redirect(url_for('services'))
	r = reddittools.get_reddit_client(redirect_uri)
	url = r.get_authorize_url(app.config["reddit"]["statekey"], 'identity', False)
	return redirect(url)

@app.route("/account/reddit/loop")
@login_required
def reddit_loop():
	query = request.args
	result = reddittools.verify_token(
			current_user.get_id(),
			query)

	if result:
		user = load_user(current_user.get_id())
		flash("Successfully updated or added reddit account: %s." % (user.redditName[0],), "success")
	else:
		flash("Failed to update reddit account.", "danger")

	return redirect(url_for("index"))

@app.route("/apiv1/group/<string:group>")
@api_key_required
def groupdump(group):
	allusers = ldaptools.getusers("authGroup=%s" % group)
	results = map(lambda x:x.characterName[0], allusers)
	return json.dumps(results)

@app.teardown_appcontext
def shutdown_session(exception=None):
	pass

import os
app.secret_key = os.urandom(24)
