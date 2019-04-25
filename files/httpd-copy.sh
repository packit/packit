#!/bin/bash

if [[ -d "/httpd-conf" ]]; then
    cp /httpd-conf/httpd-packit.conf /etc/httpd/conf.d/httpd-packit.conf
fi
