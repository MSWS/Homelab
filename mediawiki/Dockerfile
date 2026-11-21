FROM mediawiki:latest

RUN apt update && apt install -y --no-install-recommends unzip

RUN git clone --depth 1 https://gerrit.wikimedia.org/r/mediawiki/extensions/OpenIDConnect /var/www/html/extensions/OpenIDConnect
RUN git clone --depth 1 https://gerrit.wikimedia.org/r/mediawiki/extensions/PluggableAuth /var/www/html/extensions/PluggableAuth

COPY --from=composer:2 /usr/bin/composer /usr/local/bin/composer
COPY composer.local.json /var/www/html/composer.local.json

RUN composer update --no-dev --working-dir=/var/www/html
