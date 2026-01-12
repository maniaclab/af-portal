# The AF Portal web application

## Architecture

The web application follows the Model View Template (MVT) design pattern, which
is common for Python web applications. Our web server, a micro wsgi process,
forwards requests to our Python application. The Python application has request
handlers called "view functions", which handle the requests. The view functions
use templates to return dynamic HTML pages. The view functions retrieve models
from the database or from our Kubernetes cluster, and use these models to build
the templates.

## Technology

On the clientside we use jQuery, Bootstrap, DataTables, and Vue.js. For icons we
use Font Awesome. The Bootstrap framework gives us a variety of CSS classes that
we use to style our web pages. The DataTables framework helps us create reactive
tables that retrieve data using Ajax requests. It also gives us many features
like the ability to sort a table. Vue.js helps us build user interfaces out of
HTML that react to asynchronous data.

On the serverside we use a Python package called kubernetes which acts as a
Kubernetes client. kubernetes helps us manage Kubernetes objects, like pods,
services, ingresses, and secrets. We use a Python package called Flask as our
web framework. Flask helps us handle HTTP requests by means of decorator
functions that map a URL to a request handler. Flask has a templating engine
called Jinja that lets us render dynamic HTML templates.

## Authentication

We use the globus_sdk Python package to authenticate users. We authenticate
users based on their institutional login or their globus ID. We have decorator
functions in auth.py that restrict access to certain web services based on a
user's privileges (admin, member, nonmember).

## Setup

In order to set up the webapp, and run it locally, you need a portal.conf
configuration file that is properly filled out. This configuration file contains
the globus app ID, the connect API endpoint, and the location of the kubeconfig
file. You also need a kubeconfig file, at the location indicated by portal.conf,
that points to our Kubernetes cluster.

You can run the webapp in a virtual environment, and install the requirements in
a virtual environment. The command to create a virtual environment is
`python -m venv venv`. The command to activate the virtual environment is
`source venv/bin/activate`. Then you can install the requirements with the
command `pip install -r requirements.txt`. This installs all the Python packages
that are needed by the webapp.

## Running the webapp

To run the webapp locally, you can use this file (run_local.py):

    from portal import app

    if __name__ == "__main__":
        app.run(host="localhost", port="8080", debug=True)

To run this file, type

    source venv/bin/activate
    (venv) python run_local.py

Then point your browser to <http://localhost:8080> to start using the webapp.
