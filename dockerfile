FROM python:3.10-slim-buster 
WORKDIR /app 
COPY ./requirements.txt requirements.txt 
RUN apt-get update && \
    apt-get -y install gcc 
RUN pip3 install -r requirements.txt 
COPY ./app .
EXPOSE 8000 
VOLUME /data 
VOLUME /conf
ENTRYPOINT ["uvicorn","--host", "0.0.0.0", "main:app"]


