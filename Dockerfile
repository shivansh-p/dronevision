FROM mbentley/django-uwsgi-nginx
MAINTAINER ferumflex@gmail.com

RUN apt-get update && apt-get install libfreetype6-dev libjpeg-dev libjpeg62-turbo-dev -y
ADD requirements.txt /opt/django/app/requirements.txt
RUN pip install -r /opt/django/app/requirements.txt

ADD . /opt/django/app
RUN python /opt/django/app/manage.py collectstatic --noinput

VOLUME ["/opt/django/persistent/media"]
EXPOSE 80

CMD python /opt/django/app/manage.py migrate --noinput && /opt/django/run.sh
