@app.route("/instances/deploy_jupyter", methods=["GET", "POST"])
@authenticated
def deploy_jupyter():
    create_jupyter_notebook()

    return redirect(url_for("view_instances"))