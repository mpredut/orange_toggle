#!/bin/bash
# Instalează cron jobs pentru Orange Internet Toggle
# Rulează după setup.sh: bash install_cron.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/venv/bin/python"
SCRIPT="$SCRIPT_DIR/orange_internet.py"
LOG="$SCRIPT_DIR/orange.log"

# Verifică că scriptul și venv există
if [ ! -f "$PYTHON" ]; then
    echo "EROARE: Rulează mai întâi setup.sh"
    exit 1
fi

# Cron lines:
# 23:00 -> dezactivează internetul
# 05:00 -> reactivează internetul
CRON_DISABLE="0 23 * * * cd $SCRIPT_DIR && $PYTHON $SCRIPT disable >> $LOG 2>&1"
CRON_ENABLE="0 5  * * * cd $SCRIPT_DIR && $PYTHON $SCRIPT enable  >> $LOG 2>&1"

# Adaugă în crontab (evită duplicate)
(crontab -l 2>/dev/null | grep -v "orange_internet.py"; echo "$CRON_DISABLE"; echo "$CRON_ENABLE") | crontab -

echo "✅ Cron jobs instalate:"
echo "   23:00 -> dezactivează internet mobil"
echo "   05:00 -> activează internet mobil"
echo ""
echo "Verifică cu: crontab -l"
echo "Monitorizează log: tail -f $LOG"
echo ""
echo "Pentru a SCOATE cron jobs: bash remove_cron.sh"
