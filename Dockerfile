FROM python:3.7
COPY portal /app/portal
COPY markdowns /app/markdowns
COPY requirements.txt /app
COPY run_portal.py /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8080
ENV configfile /usr/local/etc/af-portal/portal.conf
CMD ["sh", "-c", "python run_portal.py ${configfile}"]