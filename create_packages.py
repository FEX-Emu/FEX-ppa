#!/bin/python3
import os
import sys
import shutil
import subprocess

# Supported distros in the form of: letter, series name
supported_distros = [
    ["f", "focal"], # Oldest supported is 20.04 focal
    ["h", "hirsute"],
    ["i", "impish"],
    ["j", "jammy"],
]

# Supported CPUs split by features
# By package suffix, -mcpu flavour
supported_cpus = [
    ["armv8.0", "cortex-a57"],
    ["armv8.2", "cortex-a75"],
    ["armv8.4", "apple-a13"], # Not quite but sure whatever
]

debfiles_tocopy = [
    "changelog",
    "control",
    "copyright",
    "files",
    "install",
    "rules",
    "fex-emu-binfmt32.install",
    "fex-emu-binfmt32.triggers",
    "fex-emu-binfmt32.postinst",
    "fex-emu-binfmt64.install",
    "fex-emu-binfmt64.triggers",
    "fex-emu-binfmt64.postinst",
    "source/",
]

def ReadFile(filename):
    if not os.path.isfile(filename):
        print("Couldn't open file! {}".format(filename))
        sys.exit()

    file = open(filename, "r")
    text = file.read()
    file.close()
    return text

def StoreFile(filename, text):
    if not os.path.isfile(filename):
        print("Couldn't open file! {}".format(filename))
        sys.exit()

    file = open(filename, "w")
    file.write(text)
    file.close()

def PrependChangelog(filename, changelog):
    changelog_file = open(filename, "r")
    original_changelog = changelog_file.read()
    changelog_file.close()
    changelog_file = open(filename, "w")
    changelog_file.write(changelog)
    changelog_file.write(original_changelog)
    changelog_file.close()

def AppendToFile(filename, text):
    _file = open(filename, "r")
    original_file = _file.read()
    _file.close()
    _file = open(filename, "w")
    _file.write(original_file)
    _file.write(text)
    _file.close()

def GetDateInCorrectFormat():
    return subprocess.getoutput("date -u -R")

# Args: <Stage> <FEX Version> <Package BaseVersion> <Base Changelog txt> <Base Source tar.gz>
if len(sys.argv) < 5:
    sys.exit()

RootBaseDeb = "deb_base"
RootGenPPA = os.path.abspath("gen_ppa")
RootPackageName = "fex-emu"
Stage = int(sys.argv[1])
FEXVersion = sys.argv[2]
RootPackageVersion = sys.argv[3]
CurrentChangelogFile = sys.argv[4]
SourceTar = sys.argv[5]

if "-" in RootPackageVersion:
    print("Can't have dash in package version. Breaks things")
    sys.exit()

if not os.path.isfile(CurrentChangelogFile):
    print("Couldn't open file! {}".format(CurrentChangelogFile))
    sys.exit()

if not os.path.isfile(SourceTar):
    print("Couldn't open file! {}".format(SourceTar))
    sys.exit()

UploaderName = "Ryan Houdek"
UploaderEmail = "houdek.ryan@fex-emu.org"

if Stage == 0:
    print("Generating Changelog")
    CurrentDate = GetDateInCorrectFormat()
    DebChangelogBase = ReadFile(RootBaseDeb + "/changelog_template")
    CurrentChangelog = ReadFile(CurrentChangelogFile)

# Replace portions of the change log that are common
    DebChangelogBase = DebChangelogBase.replace("@UPLOADER_NAME@", UploaderName)
    DebChangelogBase = DebChangelogBase.replace("@UPLOADER_EMAIL@", UploaderEmail)
    DebChangelogBase = DebChangelogBase.replace("@CHANGE_DATE@", CurrentDate)
    DebChangelogBase = DebChangelogBase.replace("@VERSION@", RootPackageVersion)
    DebChangelogBase = DebChangelogBase.replace("@CHANGE_TEXT@", CurrentChangelog)

# Prepend the changelog to the base as an update
    PrependChangelog(RootBaseDeb + "/changelog", DebChangelogBase)
    print(DebChangelogBase)

    print("\tMake sure to check {} before starting stage 2".format(RootBaseDeb + "/changelog"))

if Stage == 1:
    print("Generating debian file structure trees")
# First thing's first, bifurcate all of our options
    os.makedirs(RootGenPPA, exist_ok = True)
    for distro in supported_distros:
        for arch in supported_cpus:
            # Create subfolder
            SubFolder = RootGenPPA + "/" + RootPackageName + "-" + arch[0] + "_" + RootPackageVersion + "~" + distro[0]
            os.makedirs(SubFolder, exist_ok = True)

            # Create debian folder
            DebSubFolder = SubFolder + "/debian"
            os.makedirs(DebSubFolder, exist_ok = True)

            BaseDeb = "./" + RootBaseDeb + "/"
            ResultFolder = DebSubFolder + "/"
            # Copy over each file that needs to be straight copied
            for debfile in debfiles_tocopy:
                DebFile = BaseDeb + debfile
                if os.path.isdir(DebFile):
                    os.makedirs(ResultFolder + "/" + debfile, exist_ok = True)
                    for file in os.listdir(DebFile):
                        shutil.copy(DebFile + file, ResultFolder + debfile)
                else:
                    shutil.copy(DebFile, ResultFolder)

            # These need to be copied with rename
            # "fex-emu.install",
            # "fex-emu.postinst",
            # "fex-emu.postrm",
            # "fex-emu.triggers",
            # "libfex-emu-dev.install",
            shutil.copy(BaseDeb + "/fex-emu.install", ResultFolder + "/fex-emu-" + arch[0] + ".install")
            shutil.copy(BaseDeb + "/fex-emu.postinst", ResultFolder + "/fex-emu-" + arch[0] + ".postinst")
            shutil.copy(BaseDeb + "/fex-emu.postrm", ResultFolder + "/fex-emu-" + arch[0] + ".postrm")
            shutil.copy(BaseDeb + "/fex-emu.triggers", ResultFolder + "/fex-emu-" + arch[0] + ".triggers")
            shutil.copy(BaseDeb + "/libfex-emu-dev.install", ResultFolder + "/libfex-emu-" + arch[0] + "-dev.install")

            # Modify the changelog file in place
            SpecificChangelogFile = DebSubFolder + "/" + "changelog"
            SpecificChangelog = ReadFile(SpecificChangelogFile)
            SpecificChangelog = SpecificChangelog.replace("@DISTRO_SERIES_LETTER@", distro[0])
            SpecificChangelog = SpecificChangelog.replace("@DISTRO_SERIES@", distro[1])
            SpecificChangelog = SpecificChangelog.replace("@ARCH_SUFFIX@", arch[0])
            StoreFile(SpecificChangelogFile, SpecificChangelog)

            # Modify the rules file in place
            SpecificRulesFile = DebSubFolder + "/" + "rules"
            SpecificRules = ReadFile(SpecificRulesFile)
            SpecificRules = SpecificRules.replace("@FEX_VERSION@", FEXVersion)
            SpecificRules = SpecificRules.replace("@TUNE_CPU@", arch[1])
            StoreFile(SpecificRulesFile, SpecificRules)

            # If this is armv8.0 then append the binfmt_misc builds to its control file
            # Debian only allows one source package to provide a binary package
            SpecificControlFile = DebSubFolder + "/" + "control"
            SpecificSourceControlFile = BaseDeb + "/control." + arch[0]
            if os.path.isfile(SpecificSourceControlFile):
                SpecificSourceControl = ReadFile(SpecificSourceControlFile)
                AppendToFile(SpecificControlFile, SpecificSourceControl)

            # Modify the controls file in place
            # Generate Arch conflicts
            ArchConflicts = ""
            LibArchConflicts = ""
            for archconflict in supported_cpus:
                if arch[0] != archconflict[0]:
                    ArchConflicts = ArchConflicts + "fex-emu-" + archconflict[0] + ", "
                    LibArchConflicts = LibArchConflicts + "libfex-emu-" + archconflict[0] + "-dev, "

            # Strip ', '
            ArchConflicts = ArchConflicts[:-2]
            LibArchConflicts = LibArchConflicts[:-2]

            SpecificControl = ReadFile(SpecificControlFile)
            SpecificControl = SpecificControl.replace("@ARCH_SUFFIX@", arch[0])
            SpecificControl = SpecificControl.replace("@ARCH_CONFLICTS@", ArchConflicts)
            SpecificControl = SpecificControl.replace("@LIBARCH_CONFLICTS@", LibArchConflicts)

            StoreFile(SpecificControlFile, SpecificControl)

            # Create a softlink to the source folder which is unchanged between each distro
            # This is terrible. It doesn't even go in to the package specific folder but instead the folder above it.
            TargetSymlink = RootGenPPA + "/" + RootPackageName + "-" + arch[0] + "_" + RootPackageVersion + "~" + distro[0] + ".orig.tar.gz"
            if os.path.islink(TargetSymlink):
                os.remove(TargetSymlink)

            os.symlink(os.path.abspath(SourceTar), TargetSymlink)

if Stage == 2:
    print("Generating debuild files")
    for distro in supported_distros:
        for arch in supported_cpus:
            SubFolder = RootGenPPA + "/" + RootPackageName + "-" + arch[0] + "_" + RootPackageVersion + "~" + distro[0]
            p = subprocess.Popen(["debuild", "-S"], cwd = SubFolder)
            p.wait()
            if p.returncode != 0:
                print ("Couldn't debuild -S for some reason. Not continuing")
                sys.exit(-1)

if Stage == 3:
    print("Uploading results")
    for distro in supported_distros:
        for arch in supported_cpus:
            PackageName = RootPackageName + "-" + arch[0] + "_" + RootPackageVersion + "~" + distro[0] + "_source.changes"
            p = subprocess.Popen(["dput", "ppa:fex-emu/fex", PackageName], cwd = RootGenPPA)
            p.wait()
