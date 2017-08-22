FROM ubuntu:trusty

RUN apt-get update && apt-get install -qyy \
    -o APT::Install-Recommends=false -o APT::Install-Suggests=false \
    build-essential python-imaging git python-setuptools  ncurses-dev python-virtualenv  python-pip postgresql-client-9.3 libpq-dev \
    libpython-dev lib32ncurses5-dev pypy libffi6 openssl libgeos-dev \
    coffeescript node-less yui-compressor gcc libreadline6 libreadline6-dev patch libffi-dev libssl-dev libxml2-dev libxslt1-dev  python-dev \
    python-zmq libzmq-dev nginx libpcre3 libpcre3-dev supervisor wget libjpeg-dev libjpeg-turbo8-dev libmagic-dev

WORKDIR /tmp
RUN wget http://download.osgeo.org/gdal/1.11.0/gdal-1.11.0.tar.gz
RUN tar xvfz gdal-1.11.0.tar.gz
RUN cd gdal-1.11.0;./configure --with-python; make -j4; make install
RUN ldconfig
RUN rm -rf /tmp/* 

RUN mkdir /rapidpro
WORKDIR /rapidpro
RUN virtualenv env
RUN . env/bin/activate
ADD pip-freeze.txt /rapidpro/pip-freeze.txt
RUN pip install --upgrade pip
RUN pip install -r pip-freeze.txt --upgrade
RUN pip install uwsgi
ADD . /rapidpro
COPY settings.py.pre /rapidpro/temba/settings.py

RUN python manage.py migrate

RUN apt-get install -y curl
RUN curl -sL https://deb.nodesource.com/setup_6.x | bash -
RUN apt-get install -y nodejs
RUN npm install -g bower
RUN npm install -g less
RUN npm install -g coffee-script
RUN bower install --allow-root
RUN python manage.py collectstatic --noinput

RUN touch `echo $RANDOM`.txt

RUN python manage.py compress --extension=.haml --force

# nginx + gunicorn setup
RUN echo "daemon off;" >> /etc/nginx/nginx.conf
COPY gunicorn /etc/init/gunicorn

RUN rm -f /etc/nginx/sites-enabled/default
RUN ln -sf /rapidpro/nginx /etc/nginx/sites-enabled/

RUN rm -f /rapidpro/temba/settings.pyc

EXPOSE 8000
EXPOSE 8080

ENTRYPOINT ["/rapidpro/entrypoint.sh"]

CMD ["runserver"]

RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*[~]$ 
