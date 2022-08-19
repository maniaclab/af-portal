from portal import app

if __name__ == "__main__":
    app.run(host="localhost", port=8080, ssl_context=('./ssl/cert.pem', './ssl/key.pem'), debug=True)