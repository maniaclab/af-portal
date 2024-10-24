FROM python:3

RUN useradd -ms /bin/bash portal

WORKDIR /home/portal
RUN mkdir ./portal

COPY README.md README.md
COPY setup.py setup.py
COPY setup.cfg setup.cfg
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY boot.sh ./
COPY portal/ ./portal

RUN chmod +x boot.sh

#ENV FLASK_APP portal

USER portal

EXPOSE 5000
# ENTRYPOINT ["./boot.sh"]
