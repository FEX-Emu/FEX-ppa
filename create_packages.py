#!/bin/python3
import os
import sys
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from shutil import which

NeededApplications = [
    "debuild",
    "tree",
]

# Supported distros in the form of: letter, series name
supported_distros = [
    ["j", "jammy"],
    ["n", "noble"],
    ["o", "oracular"],
]

distro_build_depends_arch = [
    ["  mlir-14-tools",
     "  libmlir-14-dev",
     "  clang-14",
     "  clang-tools-14",
     "  clang-format-14",
     "  clang-tidy-14",
     "  clangd-14",
     "  libclang-14-dev",
     "  libstdc++-12-dev-i386-cross",
     "  libgcc-12-dev-i386-cross",
     ""],
    ["  mlir-17-tools",
     "  libmlir-17-dev",
     "  clang-17",
     "  clang-tools-17",
     "  clang-format-17",
     "  clang-tidy-17",
     "  clangd-17",
     "  libclang-17-dev",
     "  llvm-17-dev",
     "  libstdc++-13-dev-i386-cross",
     "  libgcc-13-dev-i386-cross",
     ""],
    ["  mlir-18-tools",
     "  libmlir-18-dev",
     "  clang-18",
     "  clang-tools-18",
     "  clang-format-18",
     "  clang-tidy-18",
     "  clangd-18",
     "  libclang-18-dev",
     "  llvm-18-dev",
     "  libstdc++-14-dev-i386-cross",
     "  libgcc-14-dev-i386-cross",
     ""],
]

c_compiler = [
    "clang",
    "clang-17",
    "clang-18",
]

cxx_compiler = [
    "clang++",
    "clang++-17",
    "clang++-18",
]

supports_thunks = [
    True,
    True,
    True,
]

supports_thunks_files = [
    # False
    "",
    # True
    "usr/lib/aarch64-linux-gnu/fex-emu/*\n",
]

# Supported CPUs split by features
# By package suffix, -march flavour
supported_cpus = [
    ["armv8.0", "armv8-a"],
    ["armv8.2", "armv8.2-a"],
    ["armv8.4", "armv8.4-a"],
]

shared_debfiles_tocopy = [
    "changelog",
]

debfiles_tocopy = [
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

RootBaseShared = "deb_shared"
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
UploaderEmail = "houdek.ryan@fex-emu.com"

def CheckPrograms():
    Missing = False
    for Binary in NeededApplications:
        if which(Binary) is None:
            print("Missing necessary application '{}'".format(Binary))
            Missing = True
    return not Missing

if CheckPrograms() == False:
    sys.exit(1)

if Stage == 0:
    print("Generating Changelog")
    CurrentDate = GetDateInCorrectFormat()
    DebChangelogBase = ReadFile(RootBaseShared + "/changelog_template")
    CurrentChangelog = ReadFile(CurrentChangelogFile)

# Replace portions of the change log that are common
    DebChangelogBase = DebChangelogBase.replace("@UPLOADER_NAME@", UploaderName)
    DebChangelogBase = DebChangelogBase.replace("@UPLOADER_EMAIL@", UploaderEmail)
    DebChangelogBase = DebChangelogBase.replace("@CHANGE_DATE@", CurrentDate)
    DebChangelogBase = DebChangelogBase.replace("@VERSION@", RootPackageVersion)
    DebChangelogBase = DebChangelogBase.replace("@CHANGE_TEXT@", CurrentChangelog)

# Prepend the changelog to the base as an update
    PrependChangelog(RootBaseShared + "/changelog", DebChangelogBase)
    print(DebChangelogBase)

    print("\tMake sure to check {} before starting stage 2".format(RootBaseShared + "/changelog"))

if Stage == 1:
    print("Generating debian file structure trees")
# First thing's first, bifurcate all of our options
    os.makedirs(RootGenPPA, exist_ok = True)
    distro_index = 0
    for distro in supported_distros:
        supports_thunk_option = supports_thunks[distro_index]
        thunk_files = supports_thunks_files[supports_thunk_option]
        c_compiler_override = c_compiler[distro_index]
        cxx_compiler_override = cxx_compiler[distro_index]

        distro_build_depends = ",\n".join(distro_build_depends_arch[distro_index])

        for arch in supported_cpus:
            # Create subfolder
            SubFolder = RootGenPPA + "/" + RootPackageName + "-" + arch[0] + "_" + RootPackageVersion + "~" + distro[0]
            os.makedirs(SubFolder, exist_ok = True)

            # Create debian folder
            DebSubFolder = SubFolder + "/debian"
            os.makedirs(DebSubFolder, exist_ok = True)

            BaseDeb = "./" + RootBaseDeb + "/"
            SharedBaseDeb = "./" + RootBaseShared + "/"

            ResultFolder = DebSubFolder + "/"
            # Copy over each file that needs to be straight copied
            for debfile in shared_debfiles_tocopy:
                DebFile = SharedBaseDeb + debfile
                if os.path.isdir(DebFile):
                    os.makedirs(ResultFolder + "/" + debfile, exist_ok = True)
                    for file in os.listdir(DebFile):
                        shutil.copy(DebFile + file, ResultFolder + debfile)
                else:
                    shutil.copy(DebFile, ResultFolder)

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
            # "fex-emu.triggers",
            # "libfex-emu-dev.install",
            shutil.copy(BaseDeb + "/fex-emu.install", ResultFolder + "/fex-emu-" + arch[0] + ".install")
            shutil.copy(BaseDeb + "/fex-emu.triggers", ResultFolder + "/fex-emu-" + arch[0] + ".triggers")
            shutil.copy(BaseDeb + "/libfex-emu-dev.install", ResultFolder + "/libfex-emu-" + arch[0] + "-dev.install")

            # Modify the install file in place
            SpecificInstallFile = ResultFolder + "/fex-emu-" + arch[0] + ".install"
            SpecificInstall = ReadFile(SpecificInstallFile)
            SpecificInstall = SpecificInstall.replace("@THUNK_FILES@\n", thunk_files)
            StoreFile(SpecificInstallFile, SpecificInstall)

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
            SpecificRules = SpecificRules.replace("@C_COMPILER@", c_compiler_override)
            SpecificRules = SpecificRules.replace("@CXX_COMPILER@", cxx_compiler_override)
            SpecificRules = SpecificRules.replace("@TUNE_CPU@", "generic")
            SpecificRules = SpecificRules.replace("@TUNE_ARCH@", arch[1])
            if supports_thunk_option:
                SpecificRules = SpecificRules.replace("@SUPPORTS_THUNKS@", "True")
            else:
                SpecificRules = SpecificRules.replace("@SUPPORTS_THUNKS@", "False")

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
            SpecificControl = SpecificControl.replace("@BUILD_DEPENDS_ARCH@\n", distro_build_depends)

            StoreFile(SpecificControlFile, SpecificControl)

            # Create a softlink to the source folder which is unchanged between each distro
            # This is terrible. It doesn't even go in to the package specific folder but instead the folder above it.
            TargetSymlink = RootGenPPA + "/" + RootPackageName + "-" + arch[0] + "_" + RootPackageVersion + "~" + distro[0] + ".orig.tar.gz"
            if os.path.islink(TargetSymlink):
                os.remove(TargetSymlink)

            os.symlink(os.path.abspath(SourceTar), TargetSymlink)
        distro_index += 1

@dataclass
class DebuildOutput:
    def __init__(self, Distro, Arch, LogFileName, LogFD, Process):
        self.Distro = Distro
        self.Arch = Arch
        self.LogFileName = LogFileName
        self.LogFD = LogFD
        self.Process = Process

    def Wait(self):
        self.Process.wait();

    def ErrorCode(self):
        return self.Process.returncode;

    def Close(self):
        self.LogFD.close()

    def poll(self):
        return self.Process.poll()

    def name(self):
        return "{}_{}".format(self.Arch[1], self.Distro[1])

    def pid(self):
        return self.Process.pid

def WaitForProcesses(ActiveProcesses, MaxProcesses):
    if len(ActiveProcesses) == 0:
        return ActiveProcesses

    if len(ActiveProcesses) < MaxProcesses:
        return ActiveProcesses

    DeadProcesses = []
    while True:
        for key, process in ActiveProcesses.items():
            if process.poll() != None:
                # Process exited
                ReturnCode = process.ErrorCode()
                process.Close()

                if ReturnCode != 0:
                    print ("Couldn't debuild -S for distro series {}some reason. Check log for details. Not continuing".format(process.name()))
                else:
                    print("{} completed".format(process.name()))

                DeadProcesses.append(key)

        Erased = False
        for pid in DeadProcesses:
            Erased = True
            del ActiveProcesses[pid]

        if Erased:
            break;

        # Sleep for five seconds before we poll the processes again
        time.sleep(5)

    return ActiveProcesses

if Stage == 2:
    print("Signing our license key quick to kick off a GPG wallet hit for the following processes.")
    print("\tMake sure to save to wallet so it doesn't get asked again")

    # Remove the file if it exists
    p = subprocess.Popen(["rm", "LICENSE.gpg"])
    p.wait()

    # Sign a file to store password in the wallet
    p = subprocess.Popen(["gpg", "-s", "LICENSE"])
    p.wait()
    if p.returncode != 0:
        print("Couldn't setup gpg key with signing dummy file")
        sys.exit(-1)

    print("Generating debuild files: Spinning up {} processes".format(len(supported_distros) * len(supported_cpus)))
    print("Don't kill this early otherwise you'll get background lintian processes running!")

    ActiveProcesses = {}
    for distro in supported_distros:
        for arch in supported_cpus:
            print("Building package for {} on {}.".format(arch[1], distro[1]))
            SubFolder = RootGenPPA + "/" + RootPackageName + "-" + arch[0] + "_" + RootPackageVersion + "~" + distro[0]
            SubFolderLogs = RootGenPPA + "/" + RootPackageName + "-" + arch[0] + "_" + RootPackageVersion + "~" + distro[0] + "_logs"
            os.makedirs(SubFolderLogs, exist_ok=True)
            SubFolderLogFiles = SubFolderLogs + "/log.txt"
            SubFolderLogFile = open(SubFolderLogFiles, "w")

            p = subprocess.Popen(["debuild", "-S"], cwd = SubFolder, stderr=subprocess.STDOUT, stdout=SubFolderLogFile)
            Process = DebuildOutput(distro, arch, SubFolderLogFiles, SubFolderLogFile, p)
            ActiveProcesses[Process.pid()] = Process

            # If at max processes then wait
            ActiveProcesses = WaitForProcesses(ActiveProcesses, 9)

    # Wait for all processes to exit
    ActiveProcesses = WaitForProcesses(ActiveProcesses, 0)

if Stage == 3:
    print("Uploading results")
    for distro in supported_distros:
        for arch in supported_cpus:
            PackageName = RootPackageName + "-" + arch[0] + "_" + RootPackageVersion + "~" + distro[0] + "_source.changes"
            p = subprocess.Popen(["dput", "ppa:fex-emu/fex", PackageName], cwd = RootGenPPA)
            p.wait()
