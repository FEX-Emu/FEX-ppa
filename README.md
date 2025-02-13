# Quick copy-paste guide
* From root of tree
``` bash
export TEMP_SOURCE=$(mktemp -d -t FEX-XXXXXXXXXX)
export FEX_VERSION=$(date +%y%m)
export UBUNTU_SUBVERSION= # If exists then tilde plus a number
export PACKAGE_VERSION=${FEX_VERSION}${UBUNTU_SUBVERSION}
export FEXPPA=$(readlink -f .)
git clone --recurse-submodules --depth=1 --branch=FEX-${FEX_VERSION} https://github.com/FEX-Emu/FEX.git $TEMP_SOURCE
rm -Rf $TEMP_SOURCE/External/{fex-gcc-target-tests-bins,fex-gvisor-tests-bins,fex-posixtest-bins}
rm -Rf $TEMP_SOURCE/.git
rm -Rf $TEMP_SOURCE/unittests
rm -Rf $TEMP_SOURCE/External/vixl/src/aarch32/
rm -Rf $TEMP_SOURCE/External/vixl/test
tar -cvpzf fex-emu_${PACKAGE_VERSION}.orig.tar.gz -C $TEMP_SOURCE/ .
wget https://github.com/bylaws/llvm-mingw/releases/download/20241812/llvm-mingw-20241218-ucrt-ubuntu-20.04-aarch64.tar.xz -O $TEMP_SOURCE/llvm-mingw-20241218-ucrt-ubuntu-20.04-aarch64.tar.xz
tar -cvpzf wine_fex-emu_${PACKAGE_VERSION}.orig.tar.gz -C $TEMP_SOURCE/ .
${FEXPPA}/create_packages.py 0 ${FEX_VERSION} ${PACKAGE_VERSION} TestChanges fex-emu_${PACKAGE_VERSION}.orig.tar.gz
${FEXPPA}/create_packages.py 1 ${FEX_VERSION} ${PACKAGE_VERSION} TestChanges fex-emu_${PACKAGE_VERSION}.orig.tar.gz
${FEXPPA}/create_packages.py 2 ${FEX_VERSION} ${PACKAGE_VERSION} TestChanges fex-emu_${PACKAGE_VERSION}.orig.tar.gz
# This step actually uploads the packages to launchpad.
${FEXPPA}/create_packages.py 3 ${FEX_VERSION} ${PACKAGE_VERSION} TestChanges fex-emu_${PACKAGE_VERSION}.orig.tar.gz
rm -Rf $TEMP_SOURCE
rm -Rf ${FEXPPA}/gen_ppa
rm ${FEXPPA}/fex-emu_${PACKAGE_VERSION}.orig.tar.gz
rm ${FEXPPA}/wine_fex-emu_${PACKAGE_VERSION}.orig.tar.gz
```

# Stage documentation
* `Args = <Script> <Stage> <Version> <Changelog file> <Source tar>`

## Stage 0
* Generates a change log from the passed in changelog file and copies it in to debian/changelog
* Wrapped by changelog_template
* Make sure to check debian/changelog after generating

`${FEXPPA}/create_packages.py 0 ${FEX_VERSION} ${PACKAGE_VERSION} TestChanges fex-emu_${PACKAGE_VERSION}.orig.tar.gz`

## Stage 1
* Generates all the target specific folder structures for building source packages
* Generates in to `gen_ppa` in cwd

`${FEXPPA}/create_packages.py 1 ${FEX_VERSION} ${PACKAGE_VERSION} TestChanges fex-emu_${PACKAGE_VERSION}.orig.tar.gz`

## Stage 2
* Walks all of the target specific debian trees and runs `debuild -S` over them cleanly

`${FEXPPA}/create_packages.py 2 ${FEX_VERSION} ${PACKAGE_VERSION} TestChanges fex-emu_${PACKAGE_VERSION}.orig.tar.gz`

## Stage 3
* Walks all of the created debian packages and uploads them directly to the fex-ppa with dput
* Hardcoded to ppa:fex-emu/fex

`${FEXPPA}/create_packages.py 3 ${FEX_VERSION} ${PACKAGE_VERSION} TestChanges fex-emu_${PACKAGE_VERSION}.orig.tar.gz`

# Local pbuilder testing

## Setting up a pbuilder
### Only needs to be done once
This allows you to create a pbuilder to test building the package before uploading to PPA

* Depending on which builder you want, generate an image for whichever distro series

`sudo pbuilder create --distribution jammy --architecture arm64 --mirror "http://ports.ubuntu.com/ubuntu-ports/" --basetgz /var/cache/pbuilder/jammy-arm64-base.tgz`

`sudo pbuilder create --distribution kinetic --architecture arm64 --mirror "http://ports.ubuntu.com/ubuntu-ports/" --basetgz /var/cache/pbuilder/kinetic-arm64-base.tgz`

`sudo pbuilder create --distribution noble --architecture arm64 --mirror "http://ports.ubuntu.com/ubuntu-ports/" --basetgz /var/cache/pbuilder/noble-arm64-base.tgz`

# Perform the build
This will attempt building the package provided with the dsc file.
Result will be in `/var/cache/pbuilder/result/`

`sudo pbuilder build --distribution jammy --architecture arm64 --basetgz /var/cache/pbuilder/jammy-arm64-base.tgz gen_ppa/fex-emu-armv8.0_${PACKAGE_VERSION}~j.dsc`

`sudo pbuilder build --distribution kinetic --architecture arm64 --basetgz /var/cache/pbuilder/kinetic-arm64-base.tgz gen_ppa/fex-emu-armv8.0_${PACKAGE_VERSION}~k.dsc`

`sudo pbuilder build --distribution noble --architecture arm64 --basetgz /var/cache/pbuilder/noble-arm64-base.tgz gen_ppa/fex-emu-armv8.0_${PACKAGE_VERSION}~n.dsc`

# Cleanup
` sudo rm /var/cache/pbuilder/noble-arm64-base.tgz`

## After this step you will need to do the `Setting up a pbuilder` step again

# Manual uploading to launchpad ppa

* Typically stage three of the `create_packages.py` script does this
`dput ppa:fex-emu/fex ../fex-emu_2201_source.changes`

## Common errors
### Unable to find `fex-emu_2201ubuntu4.orig.tar.gz` in upload or distribution.
* debuild -S would have printed some text about this
  * Working: dpkg-buildpackage: info: full upload (original source is included)
  * Non-working: dpkg-buildpackage: info: binary and diff upload (original source NOT included)

* Failure I found with this was changelog had multiple version back to back same versions

### Unable to find mandatory field 'Changed-By' in the changes file.
* Changes need to be indented by two spaces otherwise the change file is invalid.
* Ensure it is indented

### create_package failed with log complaining about running out of memory
* Add `auto-expand-secmem` to `$HOME/.gnupg/gpg-agent.conf` and then restart gpg-agent with `killall gpg-agent`
* Lets GPG agent allocate more secure working memory which is necessary to allow multiple signing agents at once

### New subversion rejected due to `Version older than that in the archive`
When updating the package with a new subversion, the old version first needs to be deleted from the ppa.

- This is due to their version check not really understanding the `<Version>~<SubVersion>~<distro series>` layout
