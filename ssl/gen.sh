openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Support for Microsoft Edge
# 
# Steps:
# 1. Go to edge://flags and search for localhost
# 2. Enable the flag "Allow invalid certificates for resources loaded from localhost"
