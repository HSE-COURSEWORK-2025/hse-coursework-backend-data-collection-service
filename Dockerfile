FROM python:3.10.14-bookworm

# set work directory
WORKDIR /code


# install dependencies
RUN pip3 install --upgrade pip
COPY ./requirements.txt /code/requirements.txt
RUN pip3 install -r requirements.txt

# copy project
COPY . /code/
COPY ./launch_app.sh /launch_app.sh

EXPOSE 8080

ENTRYPOINT ["sh", "/launch_app.sh"]