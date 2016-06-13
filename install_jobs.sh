#!/usr/bin/env bash

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
READ=read_environment.sh

CMD="${HERE}/${READ} >> /var/log/read_environment.log"
JOB="*/5 * * * * root ${CMD}"

# append the Cron command to crontab, removing any previous entry
cat <(fgrep -v "$READ" <(crontab -l)) <(echo "$JOB") | crontab -

