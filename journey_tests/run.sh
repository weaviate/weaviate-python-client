#!/usr/bin/env bash

function wait(){
  MAX_WAIT_SECONDS=60
  ALREADY_WAITING=0

  echo "Waiting for $1"
  while true; do
    # first check if weaviate already responds
    if ! curl -s $1 > /dev/null; then
      continue
    fi

    # endpoint available, check if it is ready
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$1/health")

    if [ "$HTTP_STATUS" -eq 200 ]; then
      break
    else
      echo "testing app is not up yet. (waited for ${ALREADY_WAITING}s)"
      if [ $ALREADY_WAITING -gt $MAX_WAIT_SECONDS ]; then
        echo "testing app did not start up in $MAX_WAIT_SECONDS."
        exit 1
      else
        sleep 2
        let ALREADY_WAITING=$ALREADY_WAITING+2
      fi
    fi
  done

  echo "testing app is up and running!"
}

pytest ./journey_tests
pip install gunicorn
pip install uvicorn
nohup gunicorn --bind=0.0.0.0:8000 --workers=2 --worker-class "uvicorn.workers.UvicornWorker" --preload journey_tests.gunicorn.app:app &
echo $! > gunicorn_pid.txt
wait "http://localhost:8000"
pytest ./journey_tests/gunicorn/test.py
kill -9 $(cat gunicorn_pid.txt)
rm gunicorn_pid.txt
