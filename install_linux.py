#!/usr/bin/env python3
"""
    Automatic installer for custom TF2 assets.
    https://github.com/PineappleTF/AssetInstaller/
    Bug reports and pull requests are welcome.

    MIT License

    Copyright (c) 2023 Pineapple.TF developers

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""

#Standard library imports:
from os import getcwd, makedirs, sep, walk
from os.path import isdir, isfile, getsize, join as path_join
from pathlib import Path
from shutil import copy2
from subprocess import Popen, PIPE



#Main function:

def main():
    """Automatically installs the downloaded TF2 asset pack onto the client's game files."""

    #We need to import getuid to ensure that the user doesn't run this script as root, but getuid only exists on Linux.
    #If the import fails, then assume that the user is on Windows and point them to the Windows .bat file.
    try:
        from os import getuid
    except ImportError:
        print('This script can only be run on Linux. Run the "install_windows.bat" file to automatically install the asset pack on Windows.')
        input("Press Enter to exit...")
        return None

    #This script should not be run as root:
    if getuid() == 0:
        print("Please re-run this script without root permissions.")
        return None

    #First, find where Steam is installed on this computer. On failure, abort:
    library_vdf = locate_steam_dir()
    if not library_vdf:
        print("ERROR: Unable to locate the Steam directory. Please launch Steam and re-run this script or install the asset pack manually.")
        return None

    #Next, find where TF2 is installed on this computer. On failure, abort:
    tf2_dir = locate_tf2_dir(library_vdf)
    if not tf2_dir:
        print("ERROR: Unable to locate the Team Fortress 2 directory. Is the game installed? Please install the asset pack manually.")
        return None

    #Now copy the contents of the asset pack to the game installation:
    copy_asset_pack_files(tf2_dir)
    print(">>> Asset pack installation successful. Launch your game and have fun!")



#Locates where Steam is installed on this computer.
#We will search for the Steam installation on the file system. Failing that, we'll search for where the currently-running Steam application was launched from.

def locate_steam_dir() -> str:
    """Searches for the directory where Steam is installed."""

    #/usr/lib/steam/bin_steam.sh looks for the Steam directory in two places:
    #
    #~/.steam/steam
    #~/.local/share/Steam/
    #
    #We will poke at both directories to find the /steamapps/libraryfolder.vdf file:
    home_dir = str(Path.home())
    libraryfolders_path = "/steamapps/libraryfolders.vdf"
    for x in ("/.steam/steam", "/.local/share/Steam/"):
        library_vdf = home_dir + x + libraryfolders_path
        if isfile(library_vdf):
            return library_vdf

    #If neither directory contains the libraryfolders.vdf file, then we'll check the Steam process to see which directory it was launched from.
    #Note that this section only applies if Steam is actively running on this computer. It will NOT work if Steam is not running!
    p = Popen("ps -aux | grep steam.sh", shell=True, stdout=PIPE)
    for x in p.stdout.read().decode().split("\n"):

        #Skip blank lines:
        if not x.strip():
            continue

        #Split along the spaces:
        split_str = x.split()

        #Search for where steam.sh is launched from:
        if split_str[-2] == "bash" and split_str[-1].endswith("/steam.sh"):

            #Extract the Steam directory path and check if it contains the libraryfolders.vdf file. If so, then we're done:
            steam_dir = str(Path(split_str[-1]).parent)
            library_vdf = steam_dir + libraryfolders_path
            if isfile(library_vdf):
                return library_vdf

    #If we weren't able to locate the Steam directory, then abort.
    return None



#Locates where TF2 is installed on this computer.
#We will search for the TF2 installation using the libraryfolders.vdf file.

def locate_tf2_dir(vdf_file: str) -> str:
    """Searches for the directory where TF2 is installed."""

    #Load the libraryfolders.vdf file and grab the main tree:
    kv = KeyValues(filename=vdf_file)
    root = kv["libraryfolders"]

    #Loop each Steam library folder:
    for x in root.values():

        #Grab its path string and apps tree:
        path = x["path"]
        apps_tree = x["apps"]

        #If app 440 (TF2) is present in the apps tree, then this is the library path where TF2 should be installed at:
        if "440" in apps_tree:

            #Build the path to the TF2 folder and check if it exists. If so, then we're done:
            tf2_folder = path_join(path, "steamapps", "common", "Team Fortress 2")
            if isdir(tf2_folder) and isfile(tf2_folder + "/hl2_linux"):
                print(">>> Found TF2 directory:", tf2_folder)
                return tf2_folder

    #If we haven't located the TF2 installation, then abort.
    return None



#Copies the contents of our asset pack to the TF2 installation.

def copy_asset_pack_files(tf2_dir: str):
    """Copies the asset pack files to the client's TF2 installation."""

    #Build the paths to our /tf/ folder and the client's /tf/ folder:
    asset_pack_dir = getcwd() + sep + "tf"
    client_dir = tf2_dir + sep + "tf"

    #Scan our /tf/ folder and calculate the file size and relative file paths of all the files that are in it:
    copy_size = 0
    files_to_copy = []
    for x in walk(asset_pack_dir):
        (current_dir, _, files_list) = x
        rel_path = current_dir.replace(asset_pack_dir, "").strip(sep)

        #Create the analogus directory in the client's TF2 folder:
        makedirs(client_dir + sep + rel_path, exist_ok=True)

        #Loop each file in this directory:
        for file in sorted(files_list):         #Sort this list so that the progress printout isn't a random messy soup

            #Clients do not need .nav or .pop files. If they want them, they can install those manually.
            #These files are included in the asset pack for community server operators to install on their servers.
            if file.endswith((".nav", ".pop")):
                continue

            #Add the file size and the relative file paths to our list of files:
            size = getsize(current_dir + sep + file)
            copy_size += size
            files_to_copy.append((rel_path + sep + file, size))

    #Now copy each file over from our asset pack directory to the client's game files:
    print(">>> Total size of assets to copy: {:.2f} MB".format(copy_size/1024/1024))
    total_copied = 0
    for x in files_to_copy:
        (rel_file_path, size) = x
        print("[{:.2f}%] Copying: {}".format(total_copied*100/copy_size, rel_file_path))
        copy2(asset_pack_dir + sep + rel_file_path, client_dir + sep + rel_file_path)       #Copy the file over
        total_copied += size



#############

#KeyValues library taken from: https://github.com/gorgitko/valve-keyvalues-python
#The library was minified to remove unused methods and functionality.

class KeyValues(dict):
    __re = __import__('re')
    __OrderedDict = __import__('collections').OrderedDict
    __regexs = {
        "key": __re.compile(r"""(['"])(?P<key>((?!\1).)*)\1(?!.)""", __re.I),
        "key_value": __re.compile(r"""(['"])(?P<key>((?!\1).)*)\1(\s+|)['"](?P<value>((?!\1).)*)\1""", __re.I)
    }
    
    def __init__(self, mapper=None, filename=None, encoding="utf-8", mapper_type=__OrderedDict, key_modifier=None, key_sorter=None):
        self.mapper_type = type(mapper) if mapper else mapper_type
        self.key_modifier = key_modifier
        self.key_sorter = key_sorter
        self.parse(filename)

    def __getitem__(self, key):
        return self.__mapper[key]

    def __key_modifier(self, key, key_modifier):
        key_modifier = key_modifier or self.key_modifier
        if key_modifier:
            return key_modifier(key)
        else:
            return key

    def __parse(self, lines, mapper_type, i=0, key_modifier=None):
        key = False
        _mapper = mapper_type()

        try:
            while i < len(lines):
                if lines[i].startswith("{"):
                    if not key:
                        raise Exception("'{{' found without key at line {}".format(i + 1))
                    _mapper[key], i = self.__parse(lines, i=i+1, mapper_type=mapper_type, key_modifier=key_modifier)
                    continue
                elif lines[i].startswith("}"):
                    return _mapper, i + 1
                elif self.__re.match(self.__regexs["key"], lines[i]):
                    key = self.__key_modifier(self.__re.search(self.__regexs["key"], lines[i]).group("key"), key_modifier)
                    i += 1
                    continue
                elif self.__re.match(self.__regexs["key_value"], lines[i]):
                    groups = self.__re.search(self.__regexs["key_value"], lines[i])
                    _mapper[self.__key_modifier(groups.group("key"), key_modifier)] = groups.group("value")
                    i += 1
                elif self.__re.match(self.__regexs["key_value"], lines[i] + lines[i+1]):
                    groups = self.__re.search(self.__regexs["key_value"], lines[i] + " " + lines[i+1])
                    _mapper[self.__key_modifier(groups.group("key"), key_modifier)] = groups.group("value")
                    i += 1
                else:
                    i += 1
        except IndexError:
            pass

        return _mapper

    def parse(self, filename, encoding="utf-8", mapper_type=__OrderedDict, key_modifier=None):
        with open(filename, mode="r", encoding=encoding) as f:
            self.__mapper = self.__parse([line.strip() for line in f.readlines()],
                                         mapper_type=mapper_type or self.mapper_type,
                                         key_modifier=key_modifier or self.key_modifier)


#############

#Execute this script
if __name__ == "__main__":
    main()


