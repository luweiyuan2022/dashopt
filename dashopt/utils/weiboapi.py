
from urllib.parse import urlencode

class OauthWeiBoAPI:
    def __init__(self,app_key,app_secret,redirect_uri):
        self.app_key=app_key
        self.app_secret=app_secret
        self.redirect_uri=redirect_uri

    def get_grant_url(self):

        params={
            "client_id":self.app_key,
            "redirect_uri":self.redirect_uri,
            "response_type":"code",
        }
        return "https://api.weibo.com/oauth2/authorize?"\
               +urlencode(params)

if __name__=='__main__':
    config={
        "app_key":"3130928110",
        "app_secret":"e305e9f04235020c05a9a18d2f3b5783",
        "redirect_uri":"http://localhost:7000/dadashop/templates/callback.html",
    }

    weibo_api=OauthWeiBoAPI(**config)
    print(weibo_api.get_grant_url())