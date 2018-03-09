FROM python:3.6

RUN apt-get update
RUN apt-get install -y vim nodejs

COPY requirements.txt /
RUN pip install -r /requirements.txt

COPY . /src

CMD cd src && python3 main.py
