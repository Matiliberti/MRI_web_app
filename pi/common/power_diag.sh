#!/bin/bash
# Power / battery diagnostics for the MRI display Pi
echo "=== MODEL ==="; cat /proc/device-tree/model; echo
echo "=== UPTIME / DATE ==="; uptime; date
echo "=== THROTTLE FLAGS (bit0=undervolt now, bit16=undervolt occurred, bit1/17=freq capped, bit2/18=throttled) ==="
vcgencmd get_throttled
echo "=== CORE VOLTAGE ==="; vcgencmd measure_volts core; vcgencmd measure_temp
echo "=== PMIC ADC (Pi 5 only: rail voltages and currents) ==="
vcgencmd pmic_read_adc 2>&1
echo "=== POWER SUPPLY MAX CURRENT (Pi 5) ==="
vcgencmd get_config usb_max_current_enable 2>/dev/null
cat /sys/firmware/devicetree/base/chosen/power/max_current 2>/dev/null | od -An -tu4 --endian=big; echo
echo "=== HWMON (any INA2xx / battery / UPS drivers) ==="
for d in /sys/class/hwmon/hwmon*; do echo "$d: $(cat $d/name 2>/dev/null)"; for f in $d/in*_input $d/curr*_input $d/power*_input; do [ -f "$f" ] && echo "  $(basename $f)=$(cat $f)"; done; done
ls /sys/class/power_supply/ 2>/dev/null && for p in /sys/class/power_supply/*; do echo "$p:"; cat $p/uevent 2>/dev/null | sed 's/^/  /'; done
echo "=== I2C DEVICES (UPS HATs usually at 0x36,0x40-0x45,0x48) ==="
which i2cdetect >/dev/null && (i2cdetect -y 1 2>&1 || sudo i2cdetect -y 1 2>&1) || echo "i2c-tools not installed"
echo "=== UNDER-VOLTAGE KERNEL MESSAGES (this boot) ==="
journalctl -k -b 0 --no-pager 2>/dev/null | grep -iE 'voltage|throttl|brown' | tail -20
echo "=== UNDER-VOLTAGE MESSAGES (previous boots) ==="
journalctl -k --no-pager 2>/dev/null | grep -iE 'under-voltage' | wc -l
echo "=== BOOT HISTORY (unexpected power loss shows as reboot without prior shutdown) ==="
journalctl --list-boots --no-pager 2>/dev/null | tail -15
echo "--- last -x ---"; last -x -n 25 2>/dev/null | grep -E 'reboot|shutdown|crash'
echo "=== LAST SHUTDOWN REASON (end of previous boot log) ==="
journalctl -b -1 --no-pager 2>/dev/null | tail -12
echo "=== DISPLAY SERVICE ==="
systemctl --no-pager status display_media 2>/dev/null | head -8
journalctl -u display_media --no-pager 2>/dev/null | tail -10
echo "=== TAILSCALE ==="; tailscale status 2>/dev/null | head -3
