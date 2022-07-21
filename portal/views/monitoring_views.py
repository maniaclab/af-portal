from flask import session, render_template, flash
from portal import logger, app, k8s_api
from portal.k8s_api import k8sException
from portal.decorators import site_member, site_admin

@app.route("/monitoring/monitor_notebooks", methods=["GET"])
@site_member
def monitor_notebooks():
    try: 
        username = session['unix_name']
        notebooks = k8s_api.get_notebooks(username)
        return render_template("my_notebooks.html", notebooks=notebooks)
    except k8sException as e:
        flash(str(e), 'warning')
    except:
        flash('Error getting Jupyter notebooks', 'warning')
    return render_template("500.html")

@app.route("/monitoring/monitor_login_nodes", methods=["GET"])
@site_admin
def monitor_login_nodes():
    return render_template("login_nodes.html")
