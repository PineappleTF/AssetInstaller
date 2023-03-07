### Automatic installer for custom TF2 assets.
### https://github.com/PineappleTF/AssetInstaller/

### MIT License
###
### Copyright (c) 2023 Pineapple.TF developers
###
### Permission is hereby granted, free of charge, to any person obtaining a copy
### of this software and associated documentation files (the "Software"), to deal
### in the Software without restriction, including without limitation the rights
### to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
### copies of the Software, and to permit persons to whom the Software is
### furnished to do so, subject to the following conditions:
###
### The above copyright notice and this permission notice shall be included in all
### copies or substantial portions of the Software.
###
### THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
### IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
### FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
### AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
### LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
### OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
### SOFTWARE.

# Enable logging
Start-Transcript -Path .\asset_installer_output.log

# Convert from VDF (Valve keyvalues format) to a PSCustomObject. Forked from https://github.com/fblz/Steam-GetOnTop
Function ConvertFrom-VDF {
    param
    (
		[Parameter(Position=0, Mandatory=$true)]
		[ValidateNotNullOrEmpty()]
        [System.String[]]$InputObject
	)
    process
    {
        $root = New-Object -TypeName PSObject
        $chain = [ordered]@{}
        $depth = 0
        $parent = $root
        $element = $null

        ForEach ($line in $InputObject)
        {
            $quotedElements = (Select-String -Pattern '(?<=")([^\"\t\s]+\s?)+(?=")' -InputObject $line -AllMatches).Matches

            if ($quotedElements.Count -eq 1) # Create a new (sub) object
            {
                $element = New-Object -TypeName PSObject
                Add-Member -InputObject $parent -MemberType NoteProperty -Name $quotedElements[0].Value -Value $element
            }
            elseif ($quotedElements.Count -eq 2) # Create a new String hash
            {
                Add-Member -InputObject $element -MemberType NoteProperty -Name $quotedElements[0].Value -Value $quotedElements[1].Value
            }
            elseif ($line -match "{")
            {
                $chain.Add($depth, $element)
                $depth++
                $parent = $chain.($depth - 1) # AKA $element

            }
            elseif ($line -match "}")
            {
                $depth--
                $parent = $chain.($depth - 1)
				$element = $parent
                $chain.Remove($depth)
            }
            else # Comments etc
            {
            }
        }

        return $root
    }
}

# Check to see if assets are available
if (Test-Path $PSScriptRoot\tf) {
	# Found asset files, continue
	Write-Output "Found asset pack."
}
else {
	# Error and quit
	Write-Error "Please extract the full zip file and run this installer again."###
	Write-Output 'Press any key to quit...';
	$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');
	Stop-Transcript
	exit
}

# Check if files have been extracted
$OSVersion = [Environment]::OSVersion.Version.Major
if (($OSVersion) -ge "10") {
	# OS is Windows 10 or 11, continue
	Write-Output "Running on a supported operating system."
}
else {
	# Error and quit
	Write-Error "This installer requires Windows 10 or higher, please upgrade your operating system! Read the README.pdf in the zip file for manual installation instructions."
	Write-Output 'Press any key to quit...';
	$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');
	Stop-Transcript
	exit
}

# Get the TF2 installation path from the registry
$TF2RegInstallPath = (Get-ChildItem HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall | ForEach-Object { Get-ItemProperty $_.PsPath } | Select-Object DisplayName,InstallLocation | Where-Object {$_.DisplayName -eq 'Team Fortress 2'}).InstallLocation

# Check to see if TF2 is installed here
if (Test-Path -Path $TF2RegInstallPath\hl2.exe) {
	$TF2InstallPath = $TF2RegInstallPath
}
else {
	# Fallback detection mechanism - parsing the libraryfolders.vdf file
	# Get Steam library locations
	$steamPath = "$((Get-ItemProperty HKCU:\Software\Valve\Steam\).SteamPath)".Replace('/','\')
	# Convert VDF to PSCustomObject
	$config = ConvertFrom-VDF (Get-Content "$($steamPath)\config\libraryfolders.vdf")
	[array]$steamLibraries += $config.libraryfolders.psobject.properties.value.path.Replace("\\", "\")
	#Deduplicate list
	$steamLibraries = $steamLibraries |  Where-Object { $_ } | Sort-Object -uniq
	# Search each library for TF2 install
	ForEach ($steamLibrary in $steamLibraries) {
	Get-ChildItem "$($steamLibrary)\SteamApps\Common\" | where-object {$_.Name -like "Team Fortress 2"} |  ForEach-Object { $TF2VDFInstallDir = $_.FullName } }
	# Check to see if TF2 is installed here
	if (Test-Path -Path $TF2VDFInstallDir\hl2.exe) {
	$TF2InstallPath = $TF2VDFInstallDir
	}
	else {
		# Error and quit
		Write-Error "TF2 install directory detection failed. Is TF2 installed on this computer? Read the README.pdf in the zip file for manual installation instructions."
		Write-Output 'Press any key to quit...';
		$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');
		Stop-Transcript
		exit
}
}

Write-Output "TF2 is installed at $($TF2InstallPath)"

# Copy the tf folder from the asset pack to the TF2 installation folder

Copy-Item -Path tf -Destination $TF2InstallPath -Recurse -PassThru -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ("Copying: {0}" -f ($_.FullName).Replace("$TF2InstallPath","")) }
Write-Output ""
Write-Output ""
Write-Output ""
Write-Output "Asset pack installation successful. Launch your game and have fun!"
Write-Output 'Press any key to exit...';
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');

Stop-Transcript