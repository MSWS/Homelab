FROM php:8.3-apache

ENV CHYRP_STORAGE_DIR=/data

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
      inotify-tools \
      libonig-dev \
      libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && docker-php-ext-install pdo_pgsql pdo_mysql

RUN mkdir -p /data/ \
    && chown -R www-data /data \
    # Use production config for PHP
    && mv "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" \
    # Raise upload_max_size to 100M
    && sed -i 's/upload_max_filesize = .*/upload_max_filesize = 100M/' "$PHP_INI_DIR/php.ini" \
    # Raise post_max_size to 100M
    && sed -i 's/post_max_size = .*/post_max_size = 100M/' "$PHP_INI_DIR/php.ini" \
    && echo "PassEnv CHYRP_STORAGE_DIR" > /etc/apache2/conf-enabled/chyrp-env.conf

COPY --chown=www-data --exclude=entrypoint.sh . /var/www/html/
COPY --chown=www-data --chmod=744 entrypoint.sh /

RUN a2enmod rewrite \
 && sed -ri 's!AllowOverride None!AllowOverride All!' /etc/apache2/apache2.conf \
 && sed -e '/^<?php/d' -e 's!%{CHYRP_PATH}/\?!!g' \
        /var/www/html/includes/htaccess.conf.php \
        > /var/www/html/.htaccess \
 && chown www-data:www-data /var/www/html/.htaccess

EXPOSE 80/tcp

VOLUME /data
VOLUME /var/www/html/uploads

USER www-data
ENTRYPOINT ["/entrypoint.sh"]
