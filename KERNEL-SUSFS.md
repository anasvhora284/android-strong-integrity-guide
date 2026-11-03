# SUSFS + KernelSU-Next kernel for your installed ROM

How to get a kernel with **KernelSU-Next + SUSFS built in** that matches the ROM you already run —
and how to install the SUSFS userspace module after.

> Worked example used throughout: OnePlus Nord 4 (SM8650-family, GKI `android14-6.1`), Axion OS 2.9
> (LineageOS kernel `6.1.176-g0dfed1b9f5b7`), KernelSU-Next 33388 + SUSFS v2.3.0. 907 vendor modules, 0 CRC
> mismatches, flashed and daily-driven.

**Always keep a copy of your stock `boot` image. Test with `fastboot boot` (RAM only) before `fastboot flash`.**

---

## 0. Which path do you need?

SUSFS is a **kernel patch** — it can't be added with a module or LKM. You need a kernel that has it.

```sh
adb shell uname -r          # e.g. 6.1.176-g0dfed1b9f5b7  →  GKI 6.1, git hash 0dfed1b9f5b7
adb shell cat /proc/version # shows the clang version the stock kernel was built with
```

| Your situation | Path |
|---|---|
| **Stock OEM firmware** (OxygenOS, ColorOS, Pixel stock…) on a GKI device | **A — prebuilt** |
| **Custom ROM** (Lineage-based: Axion, Luna, crDroid…) that ships **its own kernel** | **B — build from the ROM's kernel source** |
| Non-GKI (kernel 4.x / 5.4) | B, using the `kernel-4.x` / `kernel-5.4` SUSFS branches (harder, device-specific) |

Why custom ROMs need path B: prebuilt SUSFS kernels are built from OEM source. A custom ROM's vendor
modules (Wi-Fi, touch, display, audio…) are built against **its own** kernel; loading them on a different
kernel → symbol CRC mismatch → no Wi-Fi / touch / bootloop.

---

## Path A — prebuilt kernel (stock firmware)

- GKI devices: [WildKernels/GKI_KernelSU_SUSFS](https://github.com/WildKernels/GKI_KernelSU_SUSFS/releases)
- OnePlus stock OxygenOS/ColorOS: [WildKernels/OnePlus_KernelSU_SUSFS](https://github.com/WildKernels/OnePlus_KernelSU_SUSFS/releases)

Pick the build matching your `uname -r` (android version + kernel version + sublevel). They ship as
AnyKernel3 zips — flash from the KSU manager ("Install from storage" / AnyKernel flasher) or recovery.
Then skip to [step 6](#6-install-manager--susfs-module).

---

## Path B — build from your ROM's kernel source

Needs a Linux PC/VM (Ubuntu), ~30 GB free, `git flex bison bc libelf-dev libssl-dev dwarves python3`.
A 6.1 kernel takes ~20 min at `-j8`.

### 1. Collect from the phone (before touching anything)

```sh
adb shell uname -r                                    # exact version + -g<hash>
adb shell cat /proc/version                           # clang version
adb shell su -c 'cat /proc/config.gz' > config.gz && gunzip config.gz && mv config running_config
adb shell getprop ro.boot.slot_suffix                 # _a / _b
adb shell su -c 'cat /dev/block/by-name/boot_a' > boot_stock.img   # use your slot. KEEP THIS.

# vendor modules, for the CRC check in step 4
mkdir -p mods && adb pull /vendor_dlkm/lib/modules mods/vendor_dlkm
adb shell su -c 'ls /system_dlkm/lib/modules'         # then pull that folder too, if it exists
```

### 2. Get the exact sources

**Kernel:** find the repo your ROM builds from (usually `LineageOS/android_kernel_<vendor>_<soc>`, or the
ROM's own GitHub) and check out the commit from `uname -r`:

```sh
git clone https://github.com/LineageOS/android_kernel_oneplus_sm8650 src
cd src && git checkout 0dfed1b9f5b7 && cd ..          # the hash after -g in uname -r
```

If the hash isn't on any branch, `git fetch origin <full-sha>` works on GitHub.
Check for symlinks pointing outside the tree — many Qualcomm trees need sibling repos next to `src/`:

```sh
find src -xtype l | head        # e.g. ../sm8650-modules/..., ../sm8650-devicetrees/...
```

Clone those (`*-modules`, `*-devicetrees`) next to `src/`, at commits from the same date as the kernel
(`git log --first-parent --before=<date>`).

**Compiler:** use the **same clang** as `/proc/version` — AOSP prebuilts
`platform/prebuilts/clang/host/linux-x86`, folder `clang-rXXXXXX`. (Nord 4 / Axion: `clang-r563880c`.)

**Patches** — versions must match each other:

| Piece | Where | Note |
|---|---|---|
| KernelSU-Next | [KernelSU-Next/KernelSU-Next](https://github.com/KernelSU-Next/KernelSU-Next) | a commit/tag |
| SUSFS | [gitlab simonpunk/susfs4ksu](https://gitlab.com/simonpunk/susfs4ksu), branch **`gki-<android>-<kernel>`** (e.g. `gki-android14-6.1`) | kernel patch + `fs/` + `include/` files |
| KSU-Next ↔ SUSFS port | [WildKernels/kernel_patches](https://github.com/WildKernels/kernel_patches) `next/susfs_fix_patches/v<susfs-version>/` | KSU-Next has no official SUSFS support; these are the port |

Use the WildKernels fix folder for **the same SUSFS version** you check out, and a KSU-Next commit from the
same time. Mixing a newer SUSFS with older fix patches fails to compile/link.

### 3. Patch

```sh
cd src

# KernelSU-Next → drivers/kernelsu
curl -LSs https://raw.githubusercontent.com/KernelSU-Next/KernelSU-Next/dev/kernel/setup.sh | bash -s <ksun-commit-or-tag>

# SUSFS kernel side
cp -r ../susfs4ksu/kernel_patches/fs/* fs/
cp -r ../susfs4ksu/kernel_patches/include/* include/
patch -p1 < ../susfs4ksu/kernel_patches/50_add_susfs_in_gki-android14-6.1.patch
```

ROM trees differ slightly from Google's GKI, so a hunk or two may reject (on the LineageOS 6.1 tree:
`fs/namespace.c`, because of an extra `#include <trace/hooks/blk.h>`). Open the `.rej`, apply it by hand.

```sh
# SUSFS → KernelSU-Next side
cd KernelSU-Next       # the folder setup.sh cloned
patch -p1 < ../../susfs4ksu/kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch   # some files reject — expected
for p in ../../kernel_patches/next/susfs_fix_patches/v2.3.0/*.patch; do patch -p1 < "$p"; done
find . -name '*.rej' -o -name '*.orig' | xargs rm -f
cd ..
```

### 4. Configure & build

The two things that keep the ROM's modules loading: **identical config** and **identical version string**.

```sh
export PATH=$PWD/../clang-r563880c/bin:$PATH
M="make O=../out ARCH=arm64 LLVM=1 LLVM_IAS=1 LOCALVERSION="
mkdir -p ../out && cp ../running_config ../out/.config

scripts/config --file ../out/.config \
  -e KSU -e KSU_SUSFS -e KSU_SUSFS_SUS_PATH -e KSU_SUSFS_SUS_MOUNT -e KSU_SUSFS_SUS_KSTAT \
  -e KSU_SUSFS_SPOOF_UNAME -e KSU_SUSFS_ENABLE_LOG -e KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS \
  -e KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG -e KSU_SUSFS_OPEN_REDIRECT -e KSU_SUSFS_SUS_MAP \
  -d LOCALVERSION_AUTO --set-str LOCALVERSION "-g0dfed1b9f5b7"   # your -g<hash>
: > ../out/.scmversion                                          # stop git adding -dirty etc.
rm -f android/abi_gki_protected_exports_*                       # else a fresh signing key breaks Wi-Fi etc.

$M olddefconfig
$M -j$(nproc) Image
strings ../out/arch/arm64/boot/Image | grep -m1 'Linux version'   # must match stock uname -r
```

(`dwarves`/`pahole` is required — stock configs usually have `DEBUG_INFO_BTF=y`.)

**CRC check** — proves every ROM module will load on your kernel, before you ever boot it:

```sh
python3 tools/crc_check.py ../out/vmlinux.symvers mods/vendor_dlkm mods/system_dlkm
```

Want `0 mismatches, 0 missing`. Anything else → wrong commit, wrong config, or a patch changed an exported
struct. Don't boot it.

### 5. Pack, test, flash

Repack the stock boot image with only the kernel swapped (AOSP `mkbootimg` tools, from
`platform/system/tools/mkbootimg`):

```sh
python3 unpack_bootimg.py --boot_img boot_stock.img --out stock --format=mkbootimg > args.txt
cat args.txt   # header version, os_version, os_patch_level, cmdline...
eval python3 mkbootimg.py $(cat args.txt | sed "s#stock/kernel#../out/arch/arm64/boot/Image#") -o boot_susfs.img
```

(Or `magiskboot unpack boot_stock.img`, replace `kernel` with your `Image`, `magiskboot repack boot_stock.img`.)

```sh
adb reboot bootloader
fastboot boot boot_susfs.img            # RAM only, writes nothing. Reboot = back to stock.
```

Check in that boot: Wi-Fi, touch, display, camera, audio, and
`adb shell su -c 'dmesg | grep -iE "susfs|disagrees about version|Unknown symbol"'`
(SUSFS lines yes, the other two no).

Happy? Flash it:

```sh
adb reboot bootloader
fastboot flash boot_a boot_susfs.img            # your active slot
# Restore if anything goes wrong:
fastboot flash boot_a boot_stock.img
```

Some devices don't support `fastboot boot` — then you have to flash directly; keep `boot_stock.img` on the PC.

---

## 6. Install manager + SUSFS module

1. **KernelSU-Next manager** from [releases](https://github.com/KernelSU-Next/KernelSU-Next/releases). Its
   version must match the kernel side (UAPI). If the manager says "not installed" / "unsupported" with your
   kernel, use the manager release from the same time as your KSU-Next commit.
2. **SUSFS userspace module:** [sidex15/susfs4ksu-module](https://github.com/sidex15/susfs4ksu-module/releases)
   → install in the manager → reboot. Its WebUI (Modules → SUSFS → WebUI icon) shows kernel SUSFS version
   and lets you toggle features.
3. Sensible SUSFS toggles: `hide_cusrom`, `spoof_cmdline`, `hide_loops`, `force_hide_lsposed`,
   `hide_sus_mnts_for_all_or_non_su_procs`. Turn others on one at a time and test.
4. Then do the integrity setup in the main [README](README.md).

**Never put a file that zygote keeps open in `sus_path`** (e.g. `/system/framework/org.lineageos.platform-res.apk`)
— Chrome/Brave stop loading any page.

---

## After a ROM update

An OTA replaces `boot` → your kernel and root are gone. Redo: step 1 (new `uname -r`, new config, new stock
boot), check out the new hash, re-apply patches, update `LOCALVERSION` and patch level, build, CRC check, test, flash.
Keep your notes of which commits you used — next time is 30 minutes.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Patch rejects | ROM tree differs from GKI — apply the hunk by hand. SUSFS version ≠ WildKernels fix folder version → get matching ones |
| Build fails in `drivers/kernelsu` | KSU-Next commit too new/old for the fix patches |
| `uname -r` differs from stock | `LOCALVERSION` wrong, `.scmversion` not empty, or `LOCALVERSION_AUTO` on |
| CRC mismatches | Wrong kernel commit or config. Fix before booting |
| Boots, no Wi-Fi / touch | Modules didn't load: CRC mismatch or forgot to delete `abi_gki_protected_exports_*` |
| Stuck at logo with `fastboot boot` | Reboot (returns to stock). Check build, don't flash |
| Manager shows not installed | Manager ↔ kernel KSU version mismatch |
