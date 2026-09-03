The controls

Speaker DC and Speaker AC in ALSA are the datasheet's DCGAIN[2:0] and ACGAIN[2:0] in the Class-D Control register (R51 / 0x33). The gain table:

┌─────────┬──────────┬─────────┐
│ Setting │  Boost   │   dB    │
├─────────┼──────────┼─────────┤
│ 0       │ 1.00×    │ 0 dB    │
├─────────┼──────────┼─────────┤
│ 1       │ 1.27×    │ +2.1 dB │
├─────────┼──────────┼─────────┤
│ 2       │ 1.40×    │ +2.9 dB │
├─────────┼──────────┼─────────┤
│ 3       │ 1.52×    │ +3.6 dB │
├─────────┼──────────┼─────────┤
│ 4       │ 1.67×    │ +4.5 dB │
├─────────┼──────────┼─────────┤
│ 5       │ 1.80×    │ +5.1 dB │
├─────────┼──────────┼─────────┤
│ 6–7     │ reserved │ —       │
└─────────┴──────────┴─────────┘

Two datasheet rules that change the advice

1. DCGAIN must equal ACGAIN. The datasheet specifies setting them to the same value; mismatching them skews the Class-D DC operating point.
2. The boost is limited by your supply, or it clips. The datasheet gives:
▎ Peak output voltage = AVDD × (DCGAIN + ACGAIN)/2, and SPKVDD must be high enough to support it or the output waveform clips.

2. With the two set equal, peak = AVDD × gain. On a Pi WM8960 HAT, SPKVDD comes from the 5 V rail and AVDD is 3.3 V, so the max gain before clipping is ≈ 5.0 / 3.3 ≈ 1.5×. That means:
  - Settings 0–3 (up to 1.52×) are usable.
  - Settings 4–5 (1.67×/1.80×) need SPKVDD ≥ ~5.5–6 V — on a 5 V board they clip, which is loud but distorted/harsh, and hard on the amp and speakers.

So if you ran my earlier Speaker DC 5 / AC 5, that's very likely why it may sound bad at volume. Correct it to matched values at the ceiling:

amixer -c 3 sset 'Speaker DC' 3
amixer -c 3 sset 'Speaker AC' 3
amixer -c 3 sset 'Speaker' 100%     # main speaker vol (LOUT2VOL/ROUT2VOL), maxes at +6 dB
sudo alsactl store
(Use your current card number from cat /proc/asound/cards.)

Tune by ear: start at 3, and if you hear distortion at high output, drop both to 2. Don't go
to 4/5 unless you know the board

The honest ceiling

Even perfectly tuned, this is a  +3.6 dB of boost is roughly theuseful max; past that you're trading clipping for volume, not real output. If your speakers are rated well above 1 W and stiC = 3 with everything at 100%,the WM8960 simply can't drive them harder — that needs a small external amplifier fed from the
board's line/speaker out, not mo

Sources:
- WM8960 datasheet v4.2 (SparkFun)
- WM8960 datasheet v4.4 (Mouser)
- SparkFun WM8960 Hookup Guide

Want me to fold the working audio setup (overlay + mixer + Class-D gain rules) into the README so it's documented for the next