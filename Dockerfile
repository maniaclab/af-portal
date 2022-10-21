FROM python:3.10

RUN useradd -ms /bin/bash portal

WORKDIR /home/portal
RUN mkdir ./portal

COPY README.md README.md
# COPY setup.py setup.py
# COPY setup.cfg setup.cfg
COPY requirements.txt requirements.txt

RUN pip install -e .
RUN pip install gunicorn

COPY boot.sh ./
COPY portal/ ./portal

RUN chmod +x boot.sh

#ENV FLASK_APP servicex

USER portal

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
