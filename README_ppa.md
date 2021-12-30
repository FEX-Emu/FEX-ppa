# Source needs to be dumped in to root folder
$ rm -Rf External/{fex-gcc-target-tests-bins,fex-gvisor-tests-bins,fex-posixtest-bins}
$ rm -Rf .git
$ rm -Rf unittests
$ tar -cvpzf ../FEX-ppa/fex-emu_<MATCHING VERSION>.orig.tar.gz .

# Stage 0
# Args = <Script> <Stage> <Version> <Changelog file> <Source tar>
# Generates a change log from the passed in changelog file and copies it in to debian/changelog
# Wrapped by changelog_template
# Make sure to check debian/changelog after generating
./create_packages.py 0 2201~3 TestChanges fex-emu_2201ubuntu4.orig.tar.gz

# Stage 1
# Generates all the target specific folder structures for building source packages
# Generates in to `gen_ppa` in cwd
./create_packages.py 1 2201~3 TestChanges fex-emu_2201ubuntu4.orig.tar.gz

# Stage 2
# Walks all of the target specific debian trees and runs `debuild -S` over them cleanly
./create_packages.py 2 2201~3 TestChanges fex-emu_2201ubuntu4.orig.tar.gz

# Stage 3
# Walks all of the created debian packages and uploads them directly to the fex-ppa with dput
# Hardcoded to ppa:fex-emu/fex
./create_packages.py 3 2201~3 TestChanges fex-emu_2201ubuntu4.orig.tar.gz

# Setting up a pbuilder
## Only needs to be done once
This allows you to create a pbuilder to test building the package before uploading to PPA
$ sudo pbuilder create --distribution impish --architecture amd64 --basetgz /var/cache/pbuilder/impish-amd64-base.tgz
$ sudo pbuilder create --distribution focal --architecture amd64 --basetgz /var/cache/pbuilder/focal-amd64-base.tgz

# Perform the build
This will attempt building the package provided with the dsc file
Result will be in /var/cache/pbuilder/result/

$ sudo pbuilder build --distribution impish --architecture amd64 --basetgz /var/cache/pbuilder/impish-amd64-base.tgz ../fex-emu_2201.dsc
$ sudo pbuilder build --distribution focal --architecture amd64 --basetgz /var/cache/pbuilder/focal-amd64-base.tgz ../fex-emu_2201.dsc

# Cleanup
$ sudo rm /var/cache/pbuilder/impish-amd64-base.tgz
# After this step you will need to do the `Setting up a pbuilder` step again

# Uploading to launchpad ppa
dput ppa:fex-emu/fex ../fex-emu_2201_source.changes

# Common errors
## Unable to find `fex-emu_2201ubuntu4.orig.tar.gz` in upload or distribution.
- debuild -S would have printed some text about this
  - Working: dpkg-buildpackage: info: full upload (original source is included)
  - Non-working: dpkg-buildpackage: info: binary and diff upload (original source NOT included)

- Failure I found with this was changelog had multiple version back to back same versions

## Unable to find mandatory field 'Changed-By' in the changes file.
- Changes need to be indented by two spaces otherwise the change file is invalid.
- Ensure it is indented
