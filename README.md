# CI Connect Portal

Basecode for CI-Connect Branded [Web Portals](https://www.ci-connect.net/).

## Overview
This repository contains the base code for the CI-Connect branded portal applications. The "Portal," utilizes Globus in order to to authenticate users with [Auth](https://docs.globus.org/api/auth/). All of the Portal code can be found in the `portal/` directory.

## Getting Started
#### Set up your environment.
* [OS X](#os-x)

#### Create your own App registration for use in the Portal. 
* Visit the [Globus Developer Pages](https://developers.globus.org) to register an App.
* If this is your first time visiting the Developer Pages you'll be asked to create a Project. A Project is a way to group Apps together.
* When registering the App you'll be asked for some information, including the redirect URL and any scopes you will be requesting.
    * Redirect URL: `https://localhost:5000/authcallback` (note: if using EC2 `localhost` should be replaced with the IP address of your instance).
    * Scopes: `urn:globus:auth:scope:transfer.api.globus.org:all`, `openid`, `profile`, `email`
* After creating your App the client id and secret can be copied into this project in the following two places:
    * `portal/portal.conf` in the `PORTAL_CLIENT_ID` and `PORTAL_CLIENT_SECRET` properties.
    * `service/service.conf` where the `PORTAL_CLIENT_ID` is used to validate the access token that the Portal sends to the Service.

### OS X

##### Portal Environment Setup

* `sudo easy_install pip`
* `sudo pip install virtualenv`
* `sudo mkdir ~/projects`
* `cd ~/projects`
* `git clone https://github.com/maniaclab/ciconnect-portal`
* `cd ciconnect-portal`
* `virtualenv venv`
* `source venv/bin/activate`
* `pip install -r requirements.txt`
* Note that current `portal.conf` file located in `ciconnect-portal/portal/portal.conf` is the default .conf file from the Globus Developer Portal and will need to be updated to include correct API keys.

##### Markdown Content Setup

* `cd ~/projects`
* `git clone https://github.com/maniaclab/ciconnect-portal-markdowns`
* Make a copy of one of the branded markdown directories, label it as localhost:5000 or your local webserver
* `cp -R psdconnect.uchicago.edu/ localhost\:5000/`


##### Running the Portal App

* `cd ~/projects/ciconnect-portal`
* `./run_portal.py`
* point your browser to `https://localhost:5000`


## Branded Portal Cases

All code pertaining to individual branded portals is located in `/portal/templates/scripts.html`. This file handles stylistic differences between the portals, mainly pertaining to google analytics, nav-header menus, and branded images.


## Changes to run local environment

Update `/run_portal.py` file to match below:

```
#!/usr/bin/env python

from portal import app

if __name__ == '__main__':
    app.run(host='localhost',
            ssl_context=('./ssl/server.crt', './ssl/server.key'))
```