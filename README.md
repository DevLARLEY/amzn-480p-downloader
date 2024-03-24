# amzn-480p-downloader
Downloads any Video from Prime Video in 480p quality. (Only requires an L3 CDM)
+ Should work with 1080p if you have an L1 CDM by commenting out '&supportedDRMKeyScheme=DUAL_KEY' in get_playback_resources()

# Known supported websites
+ amazon.com
+ amazon.de
+ (amazon.co.uk)

# Installation/Usage
There are two versions:
+ One for WKS-KEYS
+ One for pywidevine directly

0. Install Python (3.7.0)
1. Install the requirements.txt file
2. Drop the file in either of those folders
3. Add an L3 CDM in the right folder
4. Add the 3 pre-defined cookies to the headers.py file
5. Add N_m3u8DL-RE to the folder if you wish to have the content downloaded, decrypted and muxed automatically
6. Change the TLD variable to you country's TLD (i.e: com = USA; de = Germany; co.uk = UK)
7. Run the script and provide a Prime Video Link.
