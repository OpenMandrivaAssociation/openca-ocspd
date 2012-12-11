#!/bin/sh

# Generates a self-signed certificate.
# Edit ocspd.cnf before running this.

OPENSSL=${OPENSSL-openssl}
SSLDIR=${SSLDIR-/etc/ssl/ocspd}
OPENSSLCONFIG=${OPENSSLCONFIG-$SSLDIR/ocspd.cnf}

CERTFILE=$SSLDIR/certs/ocspd_cert.pem
KEYFILE=$SSLDIR/private/ocspd_key.pem

if [ ! -d $SSLDIR/certs ]; then
    echo "$SSLDIR/certs directory doesn't exist"
fi

if [ ! -d $SSLDIR/private ]; then
    echo "$SSLDIR/private directory doesn't exist"
fi

if [ -f $CERTFILE ]; then
    echo "$CERTFILE already exists, won't overwrite"
    exit 1
fi

if [ -f $KEYFILE ]; then
    echo "$KEYFILE already exists, won't overwrite"
    exit 1
fi

$OPENSSL req -new -x509 -nodes -config $OPENSSLCONFIG -out $CERTFILE -keyout $KEYFILE -days 365 || exit 2
chown ocspd:ocspd $CERTFILE $KEYFILE
chmod 0600 $CERTFILE $KEYFILE
echo 
$OPENSSL x509 -subject -fingerprint -noout -in $CERTFILE || exit 2
