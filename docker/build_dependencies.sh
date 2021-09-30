#!/usr/bin/env bash
if [ $# -eq 0 ]
  then
    tag='latest'
  else
    tag=$1
fi

INITIAL_DIR=$(pwd)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# get constants
source "$DIR/constants.sh"

cd "$DIR/Dockerfiles/yeke_dependencies"
docker build -t "yake_dep:latest" .



docker ps -a

cd $INITIAL_DIR
