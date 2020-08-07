#!/bin/bash

ENDPOINT=a38islc3h7i87s-ats.iot.us-west-2.amazonaws.com
ROOTCA=certs/AmazonRootCA1.pem
CERT=certs/b1ce96c8da.cert.pem
KEY=certs/b1ce96c8da.private.key

THING=pool

PORT=/dev/ttyS0
TIMEOUT=60

./pentair-control.py --endpoint $ENDPOINT --rootCA $ROOTCA --cert $CERT --key $KEY --thingName $THING --port $PORT --timeout $TIMEOUT $1

