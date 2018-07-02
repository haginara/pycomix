FROM python:3
MAINTAINER Jonghak Choi <haginara@gmail.com>

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY comix.json.default /usr/src/app/comix.json
COPY comix.py /usr/src/app

EXPOSE 31258

CMD ["python", "./comix.py"]