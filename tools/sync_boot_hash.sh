#!/system/bin/sh
# Keep ro.boot.vbmeta.digest equal to the verifiedBootHash TEESimulator attests.
# TEESimulator harvests the real TEE's boot hash every boot into harvested.json;
# Duck ToolBox's prop handler applies /data/adb/boot_hash at boot-completed.
# Install: /data/adb/service.d/sync_boot_hash.sh (755 root:root).
H=/data/adb/teesim/harvested.json
OUT=/data/adb/boot_hash
RP=/data/adb/ksu/bin/resetprop
LOG=/data/adb/sync_boot_hash.log

btime=$(awk '/^btime/{print $2}' /proc/stat)
# Wait up to 5 min for this boot's harvest.
for _ in $(seq 1 150); do
  if [ -f "$H" ] && grep -q '"harvestFailed": false' "$H"; then
    at=$(sed -n 's/.*"harvestedAt": *\([0-9]*\).*/\1/p' "$H")
    # ms -> s as text: mksh arithmetic is 32-bit.
    [ -n "$at" ] && [ "${at%???}" -ge "$btime" ] && break
  fi
  sleep 2
done
hash=$(sed -n 's/.*"verifiedBootHash": *"\([0-9a-f]*\)".*/\1/p' "$H")
case "$hash" in
  ''|*[!0-9a-f]*|0000000000000000000000000000000000000000000000000000000000000000)
    echo "$(date '+%F %T') no valid harvest, left as is" >> "$LOG"; exit 0 ;;
esac
[ ${#hash} -eq 64 ] || exit 0
[ "$(cat "$OUT" 2>/dev/null)" = "$hash" ] || { echo "$hash" > "$OUT"; chmod 644 "$OUT"; }
# Duck's prop.sh re-applies $OUT at boot-completed; set it now and again after that.
"$RP" -n ro.boot.vbmeta.digest "$hash"
until [ "$(getprop sys.boot_completed)" = 1 ]; do sleep 2; done
sleep 10
"$RP" -n ro.boot.vbmeta.digest "$hash"
echo "$(date '+%F %T') set $hash" >> "$LOG"
