# -*- coding: utf-8 -*-

import headers
import os, re, sys, json
import base64, requests, pyfiglet, subprocess
from pywidevine.L3.cdm import cdm, deviceconfig
from pywidevine.L3.decrypt.wvdecryptcustom import WvDecrypt

def post():
    title = pyfiglet.figlet_format('AMZN 480p Key Extractor', font='speed', width=200)
    print(f'{title}')


def get_asin(url):
    a = url.split("/")
    return a[a.index("dp")+1]


def get_playback_resources(asin):
    resource_url = (f"https://atv-ps{'' if tld is 'com' else '-eu'}.amazon.{tld}/cdp/catalog/GetPlaybackResources" +
    "?deviceID=" +
    "&deviceTypeID=AOAGZA014O5RE" +
    "&firmware=1" +
    f"&asin={asin}" +
    "&consumptionType=Streaming" +
    "&desiredResources=PlaybackUrls%2CCatalogMetadata" +
    "&resourceUsage=CacheResources" +
    "&videoMaterialType=Feature" +
    "&userWatchSessionId=x" +
    "&deviceBitrateAdaptationsOverride=CVBR" +
    "&deviceDrmOverride=CENC" +
    "&supportedDRMKeyScheme=DUAL_KEY" +
    "&titleDecorationScheme=primary-content")
    return json.loads(requests.post(url=resource_url, cookies=headers.cookies).text)


def get_keys(pssh, lic_url):
    wvdecrypt = WvDecrypt(init_data_b64=pssh, cert_data_b64=None, device=deviceconfig.device_android_generic)   
    challenge = wvdecrypt.get_challenge()

    json_payload = {
        'widevine2Challenge': base64.b64encode(challenge).decode('utf-8'),
        'includeHdcpTestKeyInLicense': 'true'
    }

    license = requests.post(url=lic_url, data=json_payload, cookies=headers.cookies)

    response_json = json.loads(license.content)
    try:
        lic = response_json['widevine2License']['license']
    except Exception:
        print("Unable to obtain license from server response.")
        sys.exit()
    wvdecrypt.update_license(lic)

    return wvdecrypt.start_process()


if __name__ == '__main__':
    post()

    tld = "de"

    inp = input("ASIN / Prime Video Link: ")
    asin = get_asin(inp) if inp.startswith("http") else inp
    j = get_playback_resources(asin)

    if 'error' in j:
        print("Unable to get playback resources.")
        sys.exit()

    catalog = j["catalogMetadata"]["catalog"]
    print("\n\033[93m" + catalog['title'] + "\033[0m")
    print("\033[90m" + catalog['synopsis'] + "\033[0m")

    if not input("Get keys? (y/N): ").lower().startswith("y"):
        sys.exit()

    try:
        urls = j["playbackUrls"]["urlSets"]
    except KeyError:
        print("No manifest urls found.")
        sys.exit()

    pssh = None
    mpd_url = None
    for u in urls:
        m = urls[u]["urls"]["manifest"]["url"]
        mpd_url = m
        mpd = requests.get(url=m)
        if mpd.status_code == 200:
            res = re.findall('<cenc:pssh.*>.*<.*/cenc:pssh>', mpd.text)
            pssh = str(min([x[11:-12] for x in res], key=len)).split(">")[-1].split("<")[-1] if res else None
            if pssh is not None:
                break

    if pssh is None:
        print("No PSSH found.")
        sys.exit()

    print(f"\n{mpd_url}\n")

    lic_url = (f"https://atv-ps{'' if tld is 'com' else '-eu'}.amazon.{tld}/cdp/catalog/GetPlaybackResources?deviceID=" +
        "&deviceTypeID=AOAGZA014O5RE" +
        "&firmware=1" +
        f"&asin={asin}" +
        "&consumptionType=Streaming" +
        "&desiredResources=Widevine2License" +
        "&resourceUsage=ImmediateConsumption" +
        "&videoMaterialType=Feature" +
        "&userWatchSessionId=x")

    _, keys = get_keys(pssh, lic_url)

    for key in keys:
        print(f"--key {key} ")

    if keys and input("\nDownload and decrypt? (y/N): ").lower().startswith("y"):
        try:
            os.system(f"N_m3u8DL-RE {mpd_url} {'--key ' + ' --key '.join(keys)} -sv best -sa best -M format=mkv")
        except Exception as ex:
            print(f"Error while starting N_m3u8DL: {ex}")