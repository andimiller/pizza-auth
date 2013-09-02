from jinja2 import FileSystemLoader
from jinja2.environment import Environment
from ldaptools import LDAPTools
import smtplib
from email.mime.text import MIMEText
import time
import json

with open("config.json") as fh:
	config=json.loads(fh.read())

assert(config)

env = Environment()
env.loader = FileSystemLoader('templates')
ldaptools = LDAPTools(config)

def signup_user(user):
	email = user.email[0]
	template = env.get_template('email/signup.txt')
	return (email, "Welcome to xXPIZZAXx Services", template.render(user=user))

def send_email(to, subject, body):
	msg = MIMEText(body)
	msg['Subject'] = subject
	msg['From'] = "auth@xxpizzaxx.com"
	msg['To'] = to
	s = smtplib.SMTP('localhost')
	s.sendmail(msg['From'], msg['To'], msg.as_string())
	s.quit()


for user in ldaptools.getusers("objectClass=xxPilot"):
	print signup_user(user)

print len(ldaptools.getusers("objectClass=xxPilot"))

