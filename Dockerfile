FROM mbentley/django-uwsgi-nginx
MAINTAINER ferumflex@gmail.com

RUN apt-get update && apt-get install libfreetype6-dev libjpeg-dev libjpeg62-turbo-dev libffi-dev libssl-dev -y
ADD requirements.txt /opt/django/app/requirements.txt
RUN pip install -r /opt/django/app/requirements.txt
RUN pip uninstall -y certifi && pip install certifi==2015.04.28

ADD . /opt/django/app
RUN python /opt/django/app/manage.py collectstatic --noinput

VOLUME ["/opt/django/persistent/media"]
EXPOSE 80

CMD python /opt/django/app/manage.py migrate --noinput && /opt/django/run.sh
