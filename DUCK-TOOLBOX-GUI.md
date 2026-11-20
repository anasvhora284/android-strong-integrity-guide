# STRONG with Duck ToolBox only — every step is a tap

No PIF module, no file editing, no terminal. Button names are exactly as shown in
**Duck ToolBox v0.2.1-Stable** (checked against its source).

> Re-verified **2026-11-20** on OnePlus Nord 4 (avalon), Axion OS (Android 16): **STRONG** with Duck's built-in
> Play Integrity engine + TEESimulator + device RKP keybox, **standalone PIF module removed**.
> Current working fingerprint: **Pixel 9a (tegu), build CP4A.261105.040, patch 2026-11-05**.

---

## 0. Modules

Flash in your root manager, **one per reboot**:

1. Zygisk — [ReZygisk](https://github.com/PerformanC/ReZygisk/releases) or [Zygisk Next](https://github.com/Dr-TSNG/ZygiskNext/releases)
2. [TEESimulator](https://github.com/JingMatrix/TEESimulator/releases)
3. [Duck ToolBox](https://github.com/eltavine/Duck-ToolBox/releases)

**Uninstall** any PlayIntegrityFix / PIF inject / Tricky Store / AlwaysStrong module first, and turn off your ROM's own
spoofing (Pixel props / keybox options in ROM settings). If a PIF module is still installed, Duck's Play Integrity
**Status** shows *"Another integrity module is active"* and its engine won't start.

Open Duck ToolBox: root manager → Modules → Duck ToolBox → **WebUI** icon.

---

## 1. Get your own keybox — **Device RKP Issuer**

1. Home → **Device RKP Issuer**.
2. Under **Prerequisites** it must say **Prerequisites met** (tap **Check again** if not).
3. Leave Protocol on **Automatic (try all methods)** → tap **Issue RKP keybox** → **Continue/Confirm** on
   *"Send a request to the KeyMint TA?"*.
4. When it says **RKP keybox issued** → tap **Install to TEESimulator**.

One request per ~24 h. The keybox lasts ~2 weeks — repeat this step before it expires.
If it fails with "All available issuance methods failed", your TEE is broken — see the main [README](README.md#note-broken-tee-on-qualcomm).

## 2. TEESimulator — **Tricky Store** page

1. Home → **Tricky Store**. The card at the top should show **TEESimulator · Active**.
2. **Pick apps:** search and tick **Google Play services** and **Google Play Store** (plus any app whose
   fingerprint/biometric/UPI login fails, and Duck Detector). Tap **Save** (floating button).
3. Tap **⋮** (top right) → **Set Default Policy**.
   - **Operation Mode** → tap the **`generation`** chip (default `patch` = BASIC only).
   - Leave the patch fields alone — step 3 fills them for you.
   - Tap **Save**.
4. **⋮** → **Keybox** → should show **Installed keybox**, path `/data/adb/teesim/keybox.xml`.

## 3. Fingerprint — **Play Integrity** page

Tabs: **Status · Configuration · Fingerprints · Compatibility · Diagnostics · Licenses**

1. **Status** tab → switch on **Enable the engine**.
2. Get a fingerprint — pick **one**:

   **A. Use the tested one (recommended).**
   Download [`custom.pif.prop`](custom.pif.prop) from this repo (**Pixel 9a, patch 2026-11-05, STRONG-tested 2026-11-20**) to your phone.
   *(This one also expires — once it gives BASIC, use option B or the live sources below.)*
   **Configuration** tab → open **Import, export and raw files** → **Import** → pick `custom.pif.prop`.

   **B. Generate a fresh one** (when A has expired).
   **Fingerprints** tab → **Generate fingerprint** → wait up to 2 min until **Candidate ready for preview**.
   It picks a **random** Pixel; that's normal.

3. The **Preview changes** card opens. Check:
   - the **Field / Before / After** table has rows (empty = nothing will change);
   - **MODEL / DEVICE / FINGERPRINT** are the same Pixel.
4. In the same card, tick **Also apply this keystore patch policy (tee-simulator)**. Leave System / Vendor /
   Boot patch ticked. This sets TEESimulator's patch dates to the fingerprint's date — a mismatch gives BASIC.
5. Tap **Apply configuration**.
6. **Reboot** (first time only — the page says *"Reboot the device to finish activation"*).
   For later fingerprint changes: **Diagnostics** tab → **Restart PI processes** is enough.
7. Optional: Configuration → **Saved configurations** → name it → **Save draft as snapshot**, so you can go back
   to a working config with one tap.

## 3b. Fingerprint sources & the patch-date rule (read this)

A Pixel fingerprint is only good for a while — Google rotates/bans them. When yours gives BASIC again,
get a **fresh** one. Three sources, best first:

1. **Live ready-made list (easiest):** **[pif-json-config on SourceForge](https://sourceforge.net/projects/pif-json-config/files/)**
   — fresh Pixel **Beta/Canary** fingerprints, each already carrying a **`SECURITY_PATCH`**. Pick a **phone**
   (e.g. `Tegu` = Pixel 9a, `Tokay` = Pixel 9 — *avoid* `Tangorpro`/tablet, `Yogi`/fold), download its `.json`,
   and import it in Duck (**Configuration → Import, export and raw files → Import**).
2. **Duck's own generator:** **Fingerprints → Generate fingerprint** (picks a random current Pixel Canary).
3. **This repo's `custom.pif.prop`** (option A above) — a snapshot; expires like any other.

**The one rule that decides STRONG vs BASIC — patch dates must match.**
TEESimulator's attestation reports an **osPatchLevel**, and the Play-Integrity fingerprint reports a
**`SECURITY_PATCH`**. If they differ, you get **BASIC** even with a perfect keybox. So:

- When you **Apply configuration**, always tick **"Also apply this keystore patch policy (tee-simulator)"** —
  it copies the fingerprint's `SECURITY_PATCH` into TEESimulator's `system`/`vendor`/`boot` patch levels for you.
- Verify after: Tricky Store → ⋮ → **Set Default Policy** → **System Patch** must equal the fingerprint's
  `SECURITY_PATCH` (e.g. both `2026-11-05`). Never leave patch as `today`/auto — it drifts to the wrong month.

**Pick a build Google already accepts.** A *brand-new* Canary build (released in the last day or two) can give
BASIC until Google's servers start accepting it. If a fresh fingerprint won't go STRONG, try one that's a few
days older — `ZP11.261016.008` and `CP4A.261105.040` were both accepted in Nov 2026.

> **If a standalone PIF module gives BASIC despite a correct, patch-matched fingerprint:** on some
> KernelSU-Next + ReZygisk + Android 16 stacks the PIF *module* injects the fingerprint but Play Integrity's
> **DEVICE** check still fails (it only spoofs the main GMS process, not the isolated DroidGuard worker).
> **Duck ToolBox's built-in engine uses full injection and reaches that worker** — so on those devices Duck's
> engine is the only thing that gets STRONG. That's why this guide uses it instead of the PIF module.

## 4. Check

Run a Play Integrity checker (SPIC etc.). Expected: BASIC + DEVICE + **STRONG**.

---

## Buttons that look right but aren't

| Button | What it actually does |
|---|---|
| Fingerprints → **Fetch Pixel builds** | **Stable** Pixel builds, Pixel 6a pre-selected, **no security patch** → can't sync patch dates. A stable fingerprint gave only BASIC in earlier testing on this phone (older setup) — prefer A or B above. |
| **Match this Pixel device** | Only matches when the phone **is** a Pixel. On anything else it silently picks a random Pixel. |
| **Fill matching properties** | Copies the top fields into the `ro.*` fields of the draft. Fine — but check MODEL/DEVICE match FINGERPRINT before applying. |
| **Prepare for hardware-backed attestation** | Only sets `spoofProvider=0`. |
| **Migrate and preview** | Same as preview, also converts old PIF formats. |

## Duck Detector: Bootloader + TEE "Danger" (boot hash mismatch)

If Duck Detector says *Attested verifiedBootHash did not match ro.boot.vbmeta.digest*, the `ro.boot.vbmeta.digest`
prop doesn't match the boot hash TEESimulator attests.

- **Taps:** Tricky Store → **⋮** → **Prop Settings** → **Boot Hash** → paste the *Attested boot hash* from Duck
  Detector's Bootloader section → **Save** → reboot. Redo after every ROM update.
- **Automatic (one-time setup, needs a file copy):** put [`tools/sync_boot_hash.sh`](tools/sync_boot_hash.sh) in
  `/data/adb/service.d/` (permissions 755). Every boot it copies TEESimulator's harvested hash into Duck's boot-hash
  file and the prop, so it stays right after ROM updates.

## When it stops working

| When | Do |
|---|---|
| ~2 weeks after step 1 | Step 1 again (keybox expired) |
| Canary expired (Duck shows *Release → upstream estimated expiry*) | Step 3, option B — keep the patch-policy tick |
| After any change | Diagnostics → **Restart PI processes**, then re-check |
| Still BASIC | Tricky Store → ⋮ → **Set Default Policy**: Operation Mode must be `generation`, System Patch must equal the fingerprint's `SECURITY_PATCH` |
