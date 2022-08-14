from portal import app
from flask import session, request, render_template, url_for, redirect
import globus_sdk
from urllib.parse import urlparse, urljoin

@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")

@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html")

@app.route("/signup", methods=["GET"])
def signup():
    return render_template("signup.html")

@app.route("/login", methods=["GET"])
def login():
    redirect_uri = url_for("login", _external=True)
    client = globus_sdk.ConfidentialAppAuthClient(app.config["CLIENT_ID"], app.config["CLIENT_SECRET"])
    client.oauth2_start_flow(redirect_uri, refresh_tokens=True)
    if "code" not in request.args:
        next_url = get_safe_redirect()
        params = {"next": next_url}
        auth_uri = client.oauth2_get_authorize_url(additional_params=params)
        return redirect(auth_uri)
    else:
        code = request.args.get("code")
        tokens = client.oauth2_exchange_code_for_tokens(code)
        session.update(tokens=tokens.by_resource_server, is_authenticated=True)
        return redirect(url_for("home"))

@app.route("/logout")
def logout():
    client = globus_sdk.ConfidentialAppAuthClient(app.config["CLIENT_ID"], app.config["CLIENT_SECRET"])
    for token in (token_info["access_token"] for token_info in session["tokens"].values()):
        client.oauth2_revoke_token(token)
    session.clear()
    redirect_uri = url_for("home", _external=True)
    globus_logout_url = ("https://auth.globus.org/v2/web/logout?client=%s&redirect_uri=%s&redirect_name=Simple Portal" %(app.config["CLIENT_ID"], redirect_uri))
    return redirect(globus_logout_url)

def is_safe_redirect_url(target):
  host_url = urlparse(request.host_url)
  redirect_url = urlparse(urljoin(request.host_url, target))
  return redirect_url.scheme in ('http', 'https') and \
    host_url.netloc == redirect_url.netloc

def get_safe_redirect():
  url =  request.args.get('next')
  if url and is_safe_redirect_url(url):
    return url
  url = request.referrer
  if url and is_safe_redirect_url(url):
    return url
  return '/'
