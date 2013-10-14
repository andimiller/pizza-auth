from setuptools import setup

setup (
	name='pizza_auth',
	version='0.1',
	packages=['pizza_auth'],
	license='MIT License',
	long_description="LDAP-Backed Web Application for the management of EVE Online players and services.",
	classifiers=[
		'License :: OSI Approved :: MIT License',
		'Topic :: Internet',
		'Topic :: Communications',
		'Intended Audience :: Developers',
		'Development Status :: 3 - Alpha',
	],
	install_requires = [
		'eveapi',
		'xmpppy',
		'requests',
		'flask',
		'flask-login',
		'python-ldap',
		'python-ts3',
	]
)

