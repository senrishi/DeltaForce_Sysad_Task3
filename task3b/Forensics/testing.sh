#!/bin/bash

DIR="$HOME/chunks"

for img_path in "$DIR"/imgchunk_*; do
    filename=$(basename "$img_path")
    curl -O "http://localhost:8000/$filename"
done

for txt_path in "$DIR"/txtchunk_*; do
    filename=$(basename "$txt_path")
    curl -O "http://localhost:8000/$filename"
done
