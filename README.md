# Play Integrity STRONG on a rooted phone — TEESimulator + RKP keybox guide

> **Want it all by taps, no file editing?** → **[DUCK-TOOLBOX-GUI.md](DUCK-TOOLBOX-GUI.md)** (Duck ToolBox only, no PIF module).

A working, tested setup for passing **MEETS_STRONG_INTEGRITY** on a rooted Android phone with an
unlocked bootloader, using your **own device-minted RKP keybox** instead of hunting leaked keyboxes.

> Tested on: OnePlus Nord 4 (**avalon**, SM7675), Axion OS (Android 16), KernelSU-Next + SUSFS, November 2026.
> Integrity setups break often. If something here stops working, check the troubleshooting section first.

---

## What you need

- Rooted phone (KernelSU / KernelSU-Next / Magisk / APatch)
- A Zygisk implementation
- ADB on a PC (optional, but makes debugging much easier)
- For SUSFS root hiding: a kernel with SUSFS built in → **[KERNEL-SUSFS.md](KERNEL-SUSFS.md)** (prebuilt or build for your ROM)

## Modules

| Module | Why | Link |
|---|---|---|
| **TEESimulator** | Signs key attestations with a keybox for selected apps (the part that gives STRONG) | [JingMatrix/TEESimulator](https://github.com/JingMatrix/TEESimulator/releases) |
| **Duck ToolBox** | WebUI for **Device RKP Issuer** (mints your keybox) + its built-in **Play Integrity engine** (spoofs the Pixel fingerprint) | [eltavine/Duck-ToolBox](https://github.com/eltavine/Duck-ToolBox/releases) |
| **Zygisk** (one of) | Needed by the injection engine | [ReZygisk](https://github.com/PerformanC/ReZygisk/releases) / [Zygisk Next](https://github.com/Dr-TSNG/ZygiskNext/releases) |
| SUSFS (KernelSU only, optional) | Root hiding | [sidex15/susfs4ksu-module](https://github.com/sidex15/susfs4ksu-module/releases) |

> **Why no standalone PlayIntegrityFix module?** On a current KernelSU-Next + ReZygisk + Android 16 stack it couldn't reach STRONG in testing: v4.9-inject-s doesn't inject at all, and the Fork injects the fingerprint into GMS but **DEVICE integrity still fails** — it doesn't reach the isolated DroidGuard worker. Duck ToolBox's engine (full injection) does. Use Duck's engine; don't stack a separate PIF module on top. On older stacks the standalone module may still work — but it's not needed here.

> **Tip:** Duck ToolBox can **install and manage TEESimulator for you** from its WebUI — you don't have to flash it separately. It's still a required, distinct component (Duck doesn't do keystore attestation itself); Duck just deploys and configures it.

Debug app: **[Duck Detector](https://github.com/eltavine/Duck-Detector-Refactoring/tags)** — shows exactly what is detectable.

### Don't

- **Don't run more than one keystore hook.** Pick TEESimulator only. Remove Tricky Store, AlwaysStrong,
  "Premium Integrity" and similar — they fight each other.
- **Don't run two fingerprint engines.** Use Duck ToolBox's built-in Play Integrity engine only. If you also installed a standalone PlayIntegrityFix module, remove it — two engines fight and neither is reliable.
- **Turn off your ROM's built-in spoofing** (Pixel props / keybox / PIF options in ROM settings) — leave them all empty/disabled.
- **Install one module per reboot.** Flashing several at once can bootloop and KSU safe mode will remove them.

---

## Setup

### 1. Flash modules

Flash Zygisk → reboot → TEESimulator → reboot → Duck ToolBox → reboot.

### 2. Mint your own keybox (Device RKP Issuer)

Duck ToolBox (open its WebUI from the root manager) → **Device RKP Issuer** → scroll to the bottom → **Get RKP keybox**.

- This asks Google's RKP server for a certificate chain bound to **your** phone's real TEE. Same thing stock firmware does.
- You get one request per ~24 h. The keybox leaf is valid ~2 weeks — re-mint before it expires.
- If it fails (status `-18`, `-20`, "unsupported EEK curve"), your TEE/KeyMint is broken — see troubleshooting.

When it succeeds, use the install button it shows. **Then verify the keybox actually landed where TEESimulator reads it:**

```sh
su -c 'ls -l /data/adb/teesim/keybox.xml'
```

If it isn't there (e.g. it went to `/data/adb/tricky_store/`), copy it from Duck's output folder:

```sh
su -c 'ls -d /data/adb/duck-toolbox/var/outputs/rkp-device-*'
su -c 'cp /data/adb/duck-toolbox/var/outputs/rkp-device-<newest>/keybox.xml /data/adb/teesim/keybox.xml'
```

### 3. Configure TEESimulator — the two settings that matter

Edit `/data/adb/teesim/config.json` (or the TEESimulator / Duck WebUI). **These two are why most people get stuck at BASIC:**

| Setting | Set to | If wrong |
|---|---|---|
| `mode` | **`"generation"`** | Default `patch` uses the real TEE, which reports the bootloader as **unlocked** → BASIC only |
| `patchLevel.system` | **The same date as your fingerprint's `SECURITY_PATCH`** (e.g. `"2026-11-05"`) | `"today"` becomes the current month; if the fingerprint is from last month → mismatch → BASIC only |

Example profile:

```jsonc
{
  "version": 1,
  "profiles": {
    "default": {
      "mode": "generation",
      "keybox": "keybox.xml",
      "patchLevel": { "system": "2026-11-05", "vendor": "YYYY-MM-05", "boot": "YYYY-MM-05" },
      "apps": [
        "com.google.android.gms",
        "com.android.vending"
      ]
    }
  }
}
```

**Target apps (`apps`):** GMS + Play Store are required. Also add Duck Detector / Key Attestation (so they
see what GMS sees), and any app whose biometric / UPI / passkey login fails. On the test phone Google Pay
(`com.google.android.apps.nbu.paisa.user`), CRED, GitHub and MS Authenticator are in the list and all work.

### 4. Fingerprint (Duck ToolBox Play Integrity engine)

Duck ToolBox WebUI → **Play Integrity** → **Fetch Pixel builds** → pick one → apply. Turn the engine **on**.
Full fetch/patch-date walkthrough: **[DUCK-TOOLBOX-GUI.md § 3b](DUCK-TOOLBOX-GUI.md)**. The rules that matter:

- Use a **Google-accepted build**. A brand-new fingerprint can give BASIC until Google accepts it; if so, pick an
  older one that's known-good (e.g. a Pixel 9a `CP4A.*` or `ZP11.*` build worked in testing).
- **`MODEL` / `MANUFACTURER` must match the Pixel the `FINGERPRINT` belongs to.** Don't mix a Pixel 9a fingerprint
  with a Pixel 10 model — mismatch → BASIC. If Duck's "fill" guesses wrong, correct it by hand.
- Note the fingerprint's **`SECURITY_PATCH`** — set TEESimulator `patchLevel.system` (step 3) to the **same date**,
  or you stay at BASIC.

The current fingerprint is shown in the Duck ToolBox WebUI (Play Integrity tab).

### 5. Apply (no reboot needed)

```sh
su -c 'kill $(pidof teesim)'                       # service respawns it and reloads config
su -c 'am force-stop com.google.android.gms; am force-stop com.android.vending'
su -c 'kill $(pidof com.google.android.gms.unstable)'
```

Then check with any Play Integrity checker app (SPIC, Play Integrity API Checker).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| **BASIC only** | `mode: patch`, `system` patch = `"today"`, or no keybox in `/data/adb/teesim/` | Step 3 + verify keybox path |
| BASIC only, config correct | Fingerprint not Google-accepted yet | Fetch a known-good (older) Pixel build, re-pin patch date (step 4) |
| BASIC only, fingerprint looks right | `MODEL` / `MANUFACTURER` is a different Pixel than `FINGERPRINT` | Correct the model to match (step 4) |
| **Empty verdict** (not even BASIC, everything UNEVALUATED) | `ro.boot.vbmeta.digest` is all zeros (unlocked bootloader) | Set it to a real digest via `resetprop` at boot (SUSFS module and some integrity modules do this) |
| Device RKP Issuer fails (`-18`, `-20`) | Broken TEE/KeyMint on your ROM | Try another ROM, or on Qualcomm see note below. Meanwhile any valid keybox works in TEESimulator |
| Duck Detector flags **SELinux** | ROM is permissive / leaks SELinux state | ROM problem — modules can't fix it. Check `getenforce`; use an enforcing build |
| Duck Detector flags **TEE** | Attestation chain looks wrong (patch mode, mismatched patch level, broken TEE) | Fix step 3 first, re-scan |
| Biometric / app lock / passkey fails in some app | That app's keystore keys hit a broken real TEE | Add the app to the profile `apps` list, restart daemon, re-enroll biometric once |
| Google Pay / UPI registration fails | Another keystore hook installed (AlwaysStrong / Tricky Store broke GPay in testing) | Keep only TEESimulator; add the app to `apps` |
| Worked, then dropped after ~2 weeks | RKP keybox leaf expired | Re-mint (step 2) |
| Dropped after a new month | Pinned patch date vs new fingerprint | Re-fetch the fingerprint, re-pin `system` date (steps 3–4) |

### Quick diagnosis dump

Run in `adb shell` → `su`, and share the output when asking for help:

```sh
getenforce
grep -E '"mode"|"system"|"keybox"' /data/adb/teesim/config.json
ls -l /data/adb/teesim/keybox.xml /data/adb/tricky_store/keybox.xml 2>&1
getprop ro.boot.vbmeta.digest
ls /data/adb/modules
tail -n 30 /data/adb/teesim/log/teesim.log
```

### Note: broken TEE on Qualcomm

On the test phone the real KeyMint TA was broken (every `generateKey` → `SECURE_HW_COMMUNICATION_FAILED`,
RKP `-18`). It was repaired by re-provisioning with the vendor tool:

```sh
LD_LIBRARY_PATH=/vendor/lib64/hw /vendor/bin/KmInstallKeybox <keybox-file> attestation true
```

followed by a reboot; after that `cmd remote_provisioning csr default` returned a valid CSR and the
Device RKP Issuer worked. **Qualcomm-only, vendor-specific, at your own risk** — it is not needed if
the RKP Issuer already works for you.

---

## Notes

- Banking apps with their own root detection (e.g. Protectt.ai-based apps) can still fail with STRONG —
  that is root/hook detection, not Play Integrity. Use Duck Detector to see what they can see.
- Keep the keybox private. It is bound to your device.

## Disclaimer

For your own device only. Rooting and modifying attestation can break apps, void warranty, or trip
anti-fraud systems. No support guaranteed.
