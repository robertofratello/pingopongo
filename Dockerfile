FROM python:3.9
WORKDIR /code/app 
COPY ./requirements.txt requirements.txt 
RUN apt-get update && \
    apt-get -y install gcc 
RUN pip3 install -r requirements.txt 
COPY ./app .
EXPOSE 8000 
VOLUME /code/data 
VOLUME /code/conf
ENTRYPOINT ["uvicorn","--host", "0.0.0.0", "--reload", "main:app"]


