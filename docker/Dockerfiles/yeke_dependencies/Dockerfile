FROM library/python:3.7.1-alpine

# change to temp dir
WORKDIR /temp

# install git and build-base (GCC, etc.)
RUN apk update && apk upgrade && \
    apk add --no-cache bash git openssh && \
    apk add build-base

RUN pip install --upgrade pip
RUN pip install spacy  
RUN python -m spacy download zh_core_web_lg

RUN pip install flasgger
#Shlomo 28.4.2021 for adding keywords
RUN pip install pandas

# install requirements first to engage docker cache
RUN wget https://raw.githubusercontent.com/LIAAD/yake/master/requirements.txt -O requirements.txt
RUN pip install -r requirements.txt

# install yake via pip
RUN pip install git+https://github.com/liaad/yake.git
