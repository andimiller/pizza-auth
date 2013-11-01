from jinja2 import PackageLoader
from jinja2.environment import Environment
import smtplib
from email.mime.text import MIMEText
import time
import json
import os

class EmailTools():

	def __init__(self, config, loader):
		self.config = config
		self.env = Environment()
		self.env.loader = loader

	def send_email(self, to, subject, body):
		msg = MIMEText(body)
		msg['Subject'] = subject
		msg['From'] = "auth@" + self.config["auth"]["domain"]
		msg['To'] = to
		msg['Precedence'] = "bulk"
		msg['Auto-Submitted'] = 'auto-generated'
		s = smtplib.SMTP('localhost')
		s.sendmail(msg['From'], msg['To'], msg.as_string())
		s.quit()

	def render_email(self, to, subject, template, **kwargs):
		template = self.env.get_template("email/"+template)
		print template.render(**kwargs)
		self.send_email(to, subject, template.render(**kwargs))

