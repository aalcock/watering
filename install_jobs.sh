#!/usr/bin/env bash

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
READ=read_environment.sh

CMD=${HERE}/${READ}
JOB="*/5 * * * * root ${CMD}"
cat <(fgrep -v "$READ" <(crontab -l)) <(echo "$JOB") | crontab -