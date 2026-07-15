param(
    [ValidateSet("Install", "Speed", "Uninstall")]
    [string]$Mode = "Install"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $PSScriptRoot
$logPath = Join-Path $packageRoot "mod_manager.log"
$relativeTarget = "MeowMyCrop_Data\Managed\Assembly-CSharp.dll"
$originalHash = "ad00d6dd37d0ee222e5506e9a4b697c5b5bf10fa3673843cde68b9760654e954"
$legacyV10Hash = "6a9d6571fa9cf6f24194b565f18c5e4633941311929a929fdaf1fe70c8d6f9f2"
$variantHashes = @{
    "1" = "fd6acf0ea9d49185c835a0294199b99079c4c1a2c26ea1c74eee9c1e7616fba8"
    "2" = "a8a2785d186e21edbe7efdf072f838bcc2e086f1255305a229609d30778b1bd1"
    "5" = "527a38fbbbf0aa39a7c15a1285ebda6390f057d191be322fe5018132fa5b3efe"
    "10" = "99c8e58ec7f0cacbf083b0a56e2a665443455d086aa1760e0df2d1024803ccd3"
    "20" = "6a1cd0cf479f5c22810d8564a011ffa8bb534a9075db492a1e46fb32a6048f35"
    "50" = "ac836311c52e12bef8f8b25461a8a46cb57d4f68d5a99761066a41f54ab037c4"
    "500" = "4fd4bcb0d316faed686a4bcee791985d4193be451fcbf8d04722f2921c274625"
}

$legacyV17AutoSupplyReentryHashes = @{
    "1" = "0ff08cd4ffc52b5b6ca60ac7d4ac588d9088f981789cd33ec1fdabb0233c96b4"
    "2" = "65bb1d0b5239c0400697e6e1253245ca73ea90e0ff7f113d1ba00d99e5e7dc17"
    "5" = "1aa5ef1b53740718b55f7f074f0409ea34d9ef19cddd9ec7c461250191cd99a3"
    "10" = "1e6e870dc1290fc0c91f7e40d64685717cb628a8ba5afa41f3ba65cbd06a0948"
    "20" = "02baf004ccae110f9d014c7eb288de62d6665a4dd5c02081e11192c9d874b4fd"
    "50" = "14ec38d2c8fa6160d85ab7c157dc1a72b51c7573cd668167205105efc4bd6669"
    "500" = "1d842c602f728fa1fa8e0a2ee5c2d2710a4c21583b826e01db7d512fd855b0ff"
}

$legacyV17AutoSupplyV1Hashes = @{
    "1" = "32ae37be641f5c0f025bc35ecddf008f0b2199de8ba52fdd2b9f84cc1c4214b6"
    "2" = "fc677753a35ada8be0811e48d622b18a5952de4f0aa67cac876d06aab20e6459"
    "5" = "bba527cb7bdac8df0b02b30af0cae0c064a2b69390d5cfd3b72eab874a025d00"
    "10" = "cfc80ce7d8158dfdce217b6cb69423559f86735c2c0add0c5a0e730eecfd353d"
    "20" = "723d9fe46ab6700501281d32863fc36b0f12a920419f3597da4f16876ea9a8a0"
    "50" = "61c23795d9e53f9e51c2b68cdc3152c621938b91ca4f1d30be00394d55ba715f"
    "500" = "99d8afdc70dbc5b7e8692ffb296d069a6ba3572c5f8948ac76d1a22d7b1bff21"
}

$legacyV17EveryFrameHashes = @{
    "1" = "3338b9e8457156d869cfbfb82998b08e37d9f192c10b3b166770f9372e91af4c"
    "2" = "3cf4a1355d6b1db4ad2112cb79328692dbd9b370fc51454d1f77365badd7c91c"
    "5" = "52dbf0e1ebf010cb9ff1ec7a04e4cf6eea7f55d229b1b8df16150379d75d82a7"
    "10" = "746e1fb4c0ce92bbd1e61e8347415c0cd4965b1a69cc3c4e0ee41e3d8fb6baf6"
    "20" = "a1822fea9c384655de53a957b8d8aff702be64bc8f382f9cb2f34ec00cc1f962"
    "50" = "4ea6d68c7a69dbe9218a5f2dc06c77cdc0c8e593ed541d38c92846922766826b"
    "500" = "55c2904d9cf97281c428af5e0f36dd8fa3787e2d4f79283b5748ce13e273511c"
}

$legacyV17Hashes = @{
    "1" = "1d47232d1f9d31fe91f127316cefa888d976d9100e04886e1bab257bc2e93c7d"
    "2" = "c41d61989e1bb3d2f2e8e7582cd8adc3181c26e2375c78efa4e523d6a4f8ae8b"
    "5" = "6085f4fa43687758feb30a6be5eea5ff9dccf9b613a559af7f16c12eb822d04c"
    "10" = "c46f0b0bc8ee810badb351657cc514b3da7cd5a37b9e787986e8603ec4b25dd9"
    "20" = "9e0270b96bd1f22ec5acf8d02c8ac70e1af086a5373ed970c5985f678d2b97c4"
    "50" = "cbce1e4ea53e8b7b41ead71b87a08a7c299fe7e2f6f0e019037ff4f8dcc303b0"
}

$legacyV17Fast2Hashes = @{
    "1" = "33f412d7fe9d5e87f717c7f664b4824f8c9f08a5b1d852d672a7619800ecad7f"
    "2" = "0fd5a15099edc859f94aee5ed4e0eb8c4dcb2a930a7b2725061c3f0597a9c2d5"
    "5" = "3c798803e2daa63450085f9a96f99d647e0e07c36c62ae3448b66f049639564f"
    "10" = "9ebf1d260f3c6444963a2af855a7830ce993bb8cba048282fa5d37b6152334d8"
    "20" = "206d4661a30b756f1cc4c8f5510afa55032b7d3522bd00e88315d943dec56332"
    "50" = "ec50300f5f1eff5c97bf7819a41099814f3ea8c61eb6420a4a48b0f7d9415808"
}

$legacyV17Fast4Hashes = @{
    "1" = "205747ca878c7bc0a556bb5f60a95bd12a0e0573cacc0dab677b36f2bae45d84"
    "2" = "3cf164a47412ab6469fd760ba20a0e36c928b06927885f1c9b63d3b5fc0b3fbb"
    "5" = "8d874640e02f50b67a9a8a303d3754b76577955651b6a0ac39f4c8c2d266d87a"
    "10" = "a77aa04df07e0a1db950d07a93edebff75af99221a69481e55648074be0eedc6"
    "20" = "0eb54ffc829a5ba2ed904364427e0dab523ad345ef450b3adf43da045f857e11"
    "50" = "281d7846a28544af1153319d805e21c7f619bfe2addfacad3a87b559e147dd32"
}

$legacyV16Hashes = @{
    "1" = "fe4f3d8b26a5256fa000b5b7fe01600d7f661688b404edfdf50f11c861ffdf42"
    "2" = "9da1f8cf8aea029c529ebf6879dd9cd0b9772ea8b5c128d702281a5d070d3718"
    "5" = "71e9846570e0a6eed71062ac35bed2eb484ff816999f884c036e2109741af17d"
    "10" = "aa0c305e9b377a67449af4ec806f650db8ad271b13b26409aef92b4811d54aba"
    "20" = "aa58adc25848b96fc2fee95d9c8d69ad2e25c289abcb76f0978dfa0940ccbb97"
    "50" = "81b25919cafac31083a987b8be0a2d770fa8201412ea5bba55717153260f69ed"
}

$legacyV15Hashes = @{
    "1" = "28ff81a0a537f30727a99356e0a41068ef3dcac8c9f4b887a7d5c381dc72a317"
    "2" = "ef12d5dd40a7b26b5ff6ff0d60ddeda1437486dea69d2093b0016f777b6dba76"
    "5" = "f4b7a1f8121d99884b22e502b254f1c6630b0014d4bfa3696ad2b22319679522"
    "10" = "c7521735da2563012504bd64862afdd5944672fa6fad0db7ddb8400156f50792"
    "20" = "a24225a09eb4ca117ef846a76ca057ca8b863e01758236ea36c1b4319ac6626a"
    "50" = "27ce1ed2703c70acc2a6950333c57016f22b57cac24e6d30c2a657ea770ab99d"
}

$legacyV14Hashes = @{
    "1" = "2a127d0592918c9b9db8400fc901275f49d9ff47c31d6afdd3c4071bae5eab84"
    "2" = "08f9999091b1a0d4931ba7a9312a76195d3b3f70c64db528e4840a7a0154abf5"
    "5" = "6a4d73889d197fddb87fbf83e000720523dffb85c4e093e75370a6be3416482d"
    "10" = "489e5d694045de50bcb0a2e41bb83a9eb2b49fc3111ae71ee74c2413098e4c65"
    "20" = "baf232c6fe6c475ff8f6eed957bd50ae0634d0632f288e6ee535279902133e4b"
    "50" = "71a6476dd2775bd33d8fcae2b3761e345d0418cd7be4a7bb33c7e4f755f90793"
}

$legacyV13Hashes = @{
    "1" = "89088f13c8d93bb1bcbcf045f6a6bdd6a938dbbca81fcfc14ef001017fb91aad"
    "2" = "77c83a609c4cfba5cb4aa0dfc01edfb398168df3dbd1186e6b28b17aacd25091"
    "5" = "3390ee732212fe276e1a67ec74986045d84e92cf4f3ccf9256bfb18b69e34485"
    "10" = "7130eabada714630cf84b5bcdaf4807dba1bfab559ed1d8cc846135ab1e7899e"
    "20" = "c85f3d261ea7eaf169a673e094ad4c9d4418b3a94907c90d8796f530a004059b"
    "50" = "9758d5cc557ddbd5c7bb72e469c3df9edc41b40ff868f06f3974ab25c9c2e42c"
}

$legacyV12Hashes = @{
    "1" = "04ba0250022917b4c20e345c4c50cc8bb0fb73dbf0ac97b893dffc55c5bf9230"
    "2" = "910cd27bfd55a28189b3c42c9336d9a9129a986d6d0115c55c33ad63be2eb091"
    "5" = "b85568c9d279678c3613e805c72e5cdc46c4d2bda267a67b0767321b3e69547b"
    "10" = "65f6c7b88eeb301138524f43ec22080502fd0313c86360497cfb440205cb338d"
    "20" = "30b64a1f774c741a524c57574d028aeef9baf454d3ad4cdb6948c4acfd576fe6"
    "50" = "45cd700ef648de5fadfecf513a579e29df3a92dda4178f6784ddc3d483a04049"
}

function Show-Result([string]$Text, [string]$Title, [string]$Kind = "Info") {
    Write-Host ""
    Write-Host $Text -ForegroundColor $(if ($Kind -eq "Error") { "Red" } elseif ($Kind -eq "Success") { "Green" } else { "Cyan" })
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $icon = if ($Kind -eq "Error") { [System.Windows.Forms.MessageBoxIcon]::Error } elseif ($Kind -eq "Success") { [System.Windows.Forms.MessageBoxIcon]::Information } else { [System.Windows.Forms.MessageBoxIcon]::Information }
        [void][System.Windows.Forms.MessageBox]::Show($Text, $Title, [System.Windows.Forms.MessageBoxButtons]::OK, $icon)
    } catch { }
}

function Get-Hash([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Add-Candidate([System.Collections.Generic.List[string]]$List, [string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    try { $full = [System.IO.Path]::GetFullPath($Path) } catch { return }
    if (-not $List.Contains($full)) { $List.Add($full) }
}

function Find-GameRoot {
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    $savedPathFile = Join-Path $packageRoot "last_game_path.txt"
    if (Test-Path -LiteralPath $savedPathFile) {
        Add-Candidate $candidates ((Get-Content -LiteralPath $savedPathFile -Raw).Trim())
    }
    Add-Candidate $candidates (Get-Location).Path
    Add-Candidate $candidates $packageRoot
    Add-Candidate $candidates (Split-Path -Parent $packageRoot)

    $steamRoots = New-Object 'System.Collections.Generic.List[string]'
    try {
        $reg = Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -ErrorAction Stop
        Add-Candidate $steamRoots $reg.SteamPath
    } catch { }
    try {
        $reg = Get-ItemProperty -Path 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam' -ErrorAction Stop
        Add-Candidate $steamRoots $reg.InstallPath
    } catch { }
    if (${env:ProgramFiles(x86)}) { Add-Candidate $steamRoots (Join-Path ${env:ProgramFiles(x86)} 'Steam') }
    if ($env:ProgramFiles) { Add-Candidate $steamRoots (Join-Path $env:ProgramFiles 'Steam') }

    foreach ($steamRoot in @($steamRoots)) {
        Add-Candidate $candidates (Join-Path $steamRoot 'steamapps\common\Meow My Crop!')
        $vdf = Join-Path $steamRoot 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            foreach ($line in Get-Content -LiteralPath $vdf -ErrorAction SilentlyContinue) {
                if ($line -match '"path"\s+"([^"]+)"') {
                    $library = $matches[1] -replace '\\\\','\'
                    Add-Candidate $candidates (Join-Path $library 'steamapps\common\Meow My Crop!')
                }
            }
        }
    }
    foreach ($drive in [System.IO.DriveInfo]::GetDrives()) {
        if (-not $drive.IsReady) { continue }
        Add-Candidate $candidates (Join-Path $drive.RootDirectory.FullName 'SteamLibrary\steamapps\common\Meow My Crop!')
        Add-Candidate $candidates (Join-Path $drive.RootDirectory.FullName 'Steam\steamapps\common\Meow My Crop!')
    }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $candidate $relativeTarget)) { return $candidate }
    }

    try {
        Add-Type -AssemblyName System.Windows.Forms
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = 'Select the Meow My Crop! game folder (the folder containing MeowMyCrop.exe).'
        $dialog.ShowNewFolderButton = $false
        if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            if (Test-Path -LiteralPath (Join-Path $dialog.SelectedPath $relativeTarget)) { return $dialog.SelectedPath }
            throw "The selected folder does not contain $relativeTarget"
        }
    } catch {
        Write-Host "Folder selection failed or was cancelled: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    $typed = Read-Host 'Paste the full game folder path, or press Enter to cancel'
    if (-not [string]::IsNullOrWhiteSpace($typed)) {
        $typed = $typed.Trim('"')
        if (Test-Path -LiteralPath (Join-Path $typed $relativeTarget)) { return [System.IO.Path]::GetFullPath($typed) }
    }
    return $null
}

function Get-Game-Processes([string]$Root) {
    $expectedExe = [System.IO.Path]::GetFullPath((Join-Path $Root 'MeowMyCrop.exe'))
    $found = @()
    foreach ($proc in @(Get-Process -Name 'MeowMyCrop' -ErrorAction SilentlyContinue)) {
        $matchesThisGame = $false
        try {
            if ($proc.Path) {
                $matchesThisGame = ([System.IO.Path]::GetFullPath($proc.Path) -ieq $expectedExe)
            } else {
                # Older PowerShell/permissions may hide Path. The exact process name is still a strong match.
                $matchesThisGame = $true
            }
        } catch {
            $matchesThisGame = $true
        }
        if ($matchesThisGame) { $found += $proc }
    }
    return @($found)
}

function Ensure-Game-Closed([string]$Root) {
    while ($true) {
        $running = @(Get-Game-Processes $Root)
        if ($running.Count -eq 0) { return }

        $details = ($running | ForEach-Object {
            $pathText = ''
            try { $pathText = $_.Path } catch { }
            if ([string]::IsNullOrWhiteSpace($pathText)) { $pathText = '(path unavailable)' }
            "PID $($_.Id)  $pathText"
        }) -join "`n"

        Write-Host ''
        Write-Host 'The game process is still running:' -ForegroundColor Yellow
        Write-Host $details -ForegroundColor Yellow
        Write-Host 'The DLL cannot be replaced safely while this process is open.' -ForegroundColor Yellow

        $choice = $null
        try {
            Add-Type -AssemblyName System.Windows.Forms
            $message = "Meow My Crop is still running in the background:`n`n$details`n`nYes = close it automatically`nNo = check again after you close it yourself`nCancel = stop installation"
            $choice = [System.Windows.Forms.MessageBox]::Show(
                $message,
                'Meow My Crop MOD - Game Still Running',
                [System.Windows.Forms.MessageBoxButtons]::YesNoCancel,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            )
        } catch { }

        if ($choice -eq [System.Windows.Forms.DialogResult]::Yes) {
            foreach ($proc in $running) {
                try {
                    Stop-Process -Id $proc.Id -Force -ErrorAction Stop
                    Write-Host "Closed process PID $($proc.Id)." -ForegroundColor Green
                } catch {
                    throw "Could not close MeowMyCrop.exe (PID $($proc.Id)). Close it in Task Manager, then retry. $($_.Exception.Message)"
                }
            }
            Start-Sleep -Milliseconds 800
            continue
        }
        elseif ($choice -eq [System.Windows.Forms.DialogResult]::No) {
            Start-Sleep -Milliseconds 500
            continue
        }
        elseif ($choice -eq [System.Windows.Forms.DialogResult]::Cancel) {
            throw 'Installation cancelled because the game is still running.'
        }

        # Console fallback if Windows Forms is unavailable.
        $answer = (Read-Host 'Enter K to close the process automatically, R to recheck, or C to cancel').Trim().ToUpperInvariant()
        if ($answer -eq 'K') {
            foreach ($proc in $running) { Stop-Process -Id $proc.Id -Force -ErrorAction Stop }
            Start-Sleep -Milliseconds 800
        } elseif ($answer -eq 'C') {
            throw 'Installation cancelled because the game is still running.'
        }
    }
}

function Select-Speed([int]$DefaultSpeed = 10) {
    Write-Host ''
    Write-Host 'Choose growth speed:' -ForegroundColor Cyan
    Write-Host '  1 = 1x   (original growth per key event)'
    Write-Host '  2 = 2x'
    Write-Host '  3 = 5x'
    Write-Host '  4 = 10x  (recommended)'
    Write-Host '  5 = 20x'
    Write-Host '  6 = 50x  (very fast)'
    Write-Host '  7 = 500x (extreme)'
    $map = @{ '1'=1; '2'=2; '3'=5; '4'=10; '5'=20; '6'=50; '7'=500 }
    $choice = Read-Host "Enter 1-7 [default: 4 / ${DefaultSpeed}x]"
    if ([string]::IsNullOrWhiteSpace($choice)) { return $DefaultSpeed }
    if (-not $map.ContainsKey($choice)) { throw 'Invalid speed selection. Enter a number from 1 to 7.' }
    return [int]$map[$choice]
}

function Detect-Installed-Speed([string]$Hash) {
    foreach ($key in $variantHashes.Keys) {
        if ($variantHashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V17-Speed([string]$Hash) {
    foreach ($key in $legacyV17AutoSupplyReentryHashes.Keys) {
        if ($legacyV17AutoSupplyReentryHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17AutoSupplyV1Hashes.Keys) {
        if ($legacyV17AutoSupplyV1Hashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17EveryFrameHashes.Keys) {
        if ($legacyV17EveryFrameHashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17Hashes.Keys) {
        if ($legacyV17Hashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17Fast2Hashes.Keys) {
        if ($legacyV17Fast2Hashes[$key] -eq $Hash) { return [int]$key }
    }
    foreach ($key in $legacyV17Fast4Hashes.Keys) {
        if ($legacyV17Fast4Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V16-Speed([string]$Hash) {
    foreach ($key in $legacyV16Hashes.Keys) {
        if ($legacyV16Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V15-Speed([string]$Hash) {
    foreach ($key in $legacyV15Hashes.Keys) {
        if ($legacyV15Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V14-Speed([string]$Hash) {
    foreach ($key in $legacyV14Hashes.Keys) {
        if ($legacyV14Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V13-Speed([string]$Hash) {
    foreach ($key in $legacyV13Hashes.Keys) {
        if ($legacyV13Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

function Detect-Legacy-V12-Speed([string]$Hash) {
    foreach ($key in $legacyV12Hashes.Keys) {
        if ($legacyV12Hashes[$key] -eq $Hash) { return [int]$key }
    }
    return 0
}

$transcriptStarted = $false
try {
    Start-Transcript -Path $logPath -Append | Out-Null
    $transcriptStarted = $true
    Write-Host '=====================================================' -ForegroundColor Cyan
    Write-Host " Meow My Crop! MOD Manager v1.7 - $Mode" -ForegroundColor Cyan
    Write-Host '=====================================================' -ForegroundColor Cyan
    Write-Host "Package folder: $packageRoot"
    Write-Host "Log file: $logPath"

    $root = Find-GameRoot
    if (-not $root) { throw 'No valid game folder was selected.' }
    Ensure-Game-Closed $root
    Set-Content -LiteralPath (Join-Path $packageRoot 'last_game_path.txt') -Value $root -Encoding UTF8

    $target = Join-Path $root $relativeTarget
    $backup = "$target.meowmod_backup"
    $currentHash = Get-Hash $target
    $installedSpeed = Detect-Installed-Speed $currentHash
    $legacyV12Speed = Detect-Legacy-V12-Speed $currentHash
    $legacyV13Speed = Detect-Legacy-V13-Speed $currentHash
    $legacyV14Speed = Detect-Legacy-V14-Speed $currentHash
    $legacyV15Speed = Detect-Legacy-V15-Speed $currentHash
    $legacyV16Speed = Detect-Legacy-V16-Speed $currentHash
    $legacyV17Speed = Detect-Legacy-V17-Speed $currentHash
    $isLegacyV10 = ($currentHash -eq $legacyV10Hash)
    Write-Host "Game folder: $root"
    Write-Host "Current DLL SHA256: $currentHash"

    if ($Mode -eq 'Uninstall') {
        if (-not (Test-Path -LiteralPath $backup)) { throw 'Backup file not found. Use Steam Verify Integrity to restore the original game file.' }
        $backupHash = Get-Hash $backup
        if ($backupHash -ne $originalHash) { throw 'The backup hash is not the expected original version. It was not restored for safety.' }
        Copy-Item -LiteralPath $backup -Destination $target -Force
        if ((Get-Hash $target) -ne $originalHash) { throw 'Uninstall copy verification failed.' }
        Remove-Item -LiteralPath (Join-Path $root 'MeowMyCrop_Mod_Settings.txt') -ErrorAction SilentlyContinue
        Show-Result 'MOD uninstalled successfully. The original Assembly-CSharp.dll was restored.' 'Meow My Crop MOD' 'Success'
        exit 0
    }

    if (($currentHash -ne $originalHash) -and ($installedSpeed -eq 0) -and ($legacyV12Speed -eq 0) -and ($legacyV13Speed -eq 0) -and ($legacyV14Speed -eq 0) -and ($legacyV15Speed -eq 0) -and ($legacyV16Speed -eq 0) -and ($legacyV17Speed -eq 0) -and (-not $isLegacyV10)) {
        throw 'This Assembly-CSharp.dll is neither the supported original file nor a known v1.0/v1.2/v1.3/v1.4/v1.5/v1.6/v1.7 MOD file. The game may have updated or another MOD may already modify it.'
    }
    if ($isLegacyV10) {
        Write-Host 'Detected v1.0 MOD. It can be upgraded directly to v1.7.' -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.0 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.7.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.0 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV17Speed -gt 0) {
        Write-Host "Detected earlier v1.7 (${legacyV17Speed}x). Updating automatic can supply with exchange reentry protection." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'An earlier v1.7 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.7.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'Earlier v1.7 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV16Speed -gt 0) {
        Write-Host "Detected v1.6 (${legacyV16Speed}x). v1.7 adds four independent persistent feature switches." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.6 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.7.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.6 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV15Speed -gt 0) {
        Write-Host "Detected v1.5 (${legacyV15Speed}x). v1.6 adds automatic can opening and local Legendary/orange decoration rarity." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.5 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.7.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.5 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV14Speed -gt 0) {
        Write-Host "Detected v1.4 (${legacyV14Speed}x). v1.5 removes the one-fruit skip and guarantees automatic steal/lost events." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.4 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.7.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.4 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV13Speed -gt 0) {
        Write-Host "Detected v1.3 (${legacyV13Speed}x). v1.7 will preserve automatic offline steal and automatic being-stolen events." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.3 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.7.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.3 backup hash is unexpected. It was not overwritten for safety.' }
    }
    if ($legacyV12Speed -gt 0) {
        Write-Host "Detected v1.2 (${legacyV12Speed}x). v1.7 will repair input handling and guarantee automatic offline steal/loss events." -ForegroundColor Yellow
        if (-not (Test-Path -LiteralPath $backup)) { throw 'v1.2 is installed but its original backup was not found. Use Steam Verify Integrity first, then install v1.7.' }
        if ((Get-Hash $backup) -ne $originalHash) { throw 'v1.2 backup hash is unexpected. It was not overwritten for safety.' }
    }

    $defaultSpeed = if ($installedSpeed -gt 0) { $installedSpeed } elseif ($legacyV17Speed -gt 0) { $legacyV17Speed } elseif ($legacyV16Speed -gt 0) { $legacyV16Speed } elseif ($legacyV15Speed -gt 0) { $legacyV15Speed } elseif ($legacyV14Speed -gt 0) { $legacyV14Speed } elseif ($legacyV13Speed -gt 0) { $legacyV13Speed } elseif ($legacyV12Speed -gt 0) { $legacyV12Speed } else { 10 }
    $speed = Select-Speed $defaultSpeed
    $modDll = Join-Path $packageRoot ("ModFiles\Assembly-CSharp_{0}x.dll" -f $speed)
    if (-not (Test-Path -LiteralPath $modDll)) { throw "Missing MOD variant: $modDll" }
    if ((Get-Hash $modDll) -ne $variantHashes[[string]$speed]) { throw 'MOD package integrity check failed. Re-extract the ZIP.' }

    if ($currentHash -eq $originalHash) {
        if (-not (Test-Path -LiteralPath $backup)) {
            Copy-Item -LiteralPath $target -Destination $backup -Force
            Write-Host "Original backup created: $backup" -ForegroundColor Yellow
        } elseif ((Get-Hash $backup) -ne $originalHash) {
            throw 'An existing backup file has an unexpected hash. Rename or remove it only after keeping a safe copy.'
        }
    }

    Copy-Item -LiteralPath $modDll -Destination $target -Force
    if ((Get-Hash $target) -ne $variantHashes[[string]$speed]) { throw 'Installation copy verification failed.' }
    @(
        'Meow My Crop! AutoFarm MOD v1.7',
        "GrowthSpeed=${speed}x",
        'F5=Toggle automatic steal + automatic being-stolen (persistent)',
        'F6=Toggle internal automatic key delivery (persistent; physical input remains active)',
        'F7=Toggle automatic harvest + replant (persistent)',
        'F8=Toggle automatic can opening + missing-fruit crop supply (persistent)',
        'All four switches default to enabled on first run',
        'DecorationRarityOverride=Local Legendary/orange display and classification',
        'No mouse movement or mouse capture is used',
        "Installed=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    ) | Set-Content -LiteralPath (Join-Path $root 'MeowMyCrop_Mod_Settings.txt') -Encoding UTF8

    $verb = if ($Mode -eq 'Speed') { 'Growth speed changed' } else { 'MOD v1.7 installed' }
    Show-Result "$verb successfully.`nGrowth speed: ${speed}x`n`nIndependent persistent switches (default ON):`nF5 = steal + being-stolen`nF6 = internal automatic key delivery`nF7 = automatic harvest + replant`nF8 = automatic can opening + missing-fruit crop supply`n`nWhen a can lacks fruit, the current wrong crop is removed and the required crop is planted with synchronized visuals. Manual keyboard/mouse input and the manual can button remain usable." 'Meow My Crop MOD' 'Success'
    exit 0
}
catch {
    $message = $_.Exception.Message
    Write-Host ''
    Write-Host "FAILED: $message" -ForegroundColor Red
    Write-Host "Detailed log: $logPath" -ForegroundColor Yellow
    Show-Result "Operation failed:`n$message`n`nDetailed log:`n$logPath" 'Meow My Crop MOD - Error' 'Error'
    exit 1
}
finally {
    if ($transcriptStarted) { try { Stop-Transcript | Out-Null } catch { } }
}
