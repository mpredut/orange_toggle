#!/bin/bash
# Șterge cron jobs Orange
(crontab -l 2>/dev/null | grep -v "orange_internet.py") | crontab -
echo "✅ Cron jobs Orange au fost șterse."
crontab -l
