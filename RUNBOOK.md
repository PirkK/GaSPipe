export LOG_LEVEL=DEBUG
python -m src.gaspipe.cli self-test
ffmpeg -version
# Estrarre logs JSON: jq '. | select(.run_id=="<id>")' logs.json
