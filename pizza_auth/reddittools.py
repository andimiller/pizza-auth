#!/usr/bin/env python

import praw
from flask import url_for
from hashlib import sha1

class RedditTools():
	def __init__(self, config, ldaptools):
		self.authconfig = config
		self.config = config["reddit"]
                self.ldaptools = ldaptools

                self.ldaptools.User.get_reddit_token = lambda x:hasattr(x, "redditToken") and x.redditToken[0] or None
                self.ldaptools.User.get_reddit_name  = lambda x:hasattr(x, "redditName") and x.redditName[0] or None

        def get_reddit_client(self, redirect_uri):
            r = praw.Reddit(
                    self.config["clientname"]
                    )

            r.set_oauth_app_info(
                    client_id = self.config["clientid"],
                    client_secret = self.config["clientsecret"],
                    redirect_uri = redirect_uri
                    )

            return r

        def verify_token(self, uid, query_args):
            code = query_args.get('code', None)
            state = query_args.get('state', None)
            user = self.ldaptools.getuser(uid)

            if code and state:
                state_key = self.config["statekey"]
                if state_key == state:
                    r = self.get_reddit_client("http://newauth.talkinlocal.org" + url_for('reddit_loop'))
                    access_info = r.get_access_information(code)
                    auth_reddit = r.get_me()
                    if 'redditAccount' in user.objectClass:
                        if hasattr(user, 'redditName') and hasattr(user, 'redditToken'):
                            from ldap import MOD_REPLACE
                            self.ldaptools.updateattrs(uid, MOD_REPLACE, {
                                'redditName': auth_reddit.name,
                                'redditToken': access_info['access_token']
                                })
                        else:
                            # Something went horribly wrong.
                            return False
                    else:
                        from ldap import MOD_ADD
                        self.ldaptools.updateattrs(uid, MOD_ADD, {
                            'objectClass': 'redditAccount',
                            'redditName': auth_reddit.name,
                            'redditToken': access_info['access_token']
                            })

                    return True
                    
            return False

        def get_auth_url(self):
            state_key = self.config["statekey"]
            redirect_uri = "http://newauth.talkinlocal.org" + url_for('reddit_loop')
            r = self.get_reddit_client(redirect_uri)
            url = r.get_authorize_url(state_key, 'identity', False)

            return url
