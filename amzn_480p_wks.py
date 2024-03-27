# -*- coding: utf-8 -*-
import urllib.parse

import headers
import os, sys, json
import base64, requests, pyfiglet, xmltodict
from pywidevine.L3.cdm import deviceconfig
from pywidevine.L3.decrypt.wvdecryptcustom import WvDecrypt
import browser_cookie3


def post():
    title = pyfiglet.figlet_format('AMZN 480p Key Extractor', font='speed', width=200)
    print(f'{title}')


def extract_pssh(xml):
    pssh = []
    try:
        mpd = json.loads(json.dumps(xml))
        periods = mpd['MPD']['Period']
    except Exception:
        return
    if isinstance(periods, list):
        maxHeight = 0
        for p in periods:
            for ad_set in p['AdaptationSet']:
                if 'ContentProtection' not in ad_set:
                    continue
                if '@maxHeight' not in ad_set:
                    continue
                if int(ad_set["@maxHeight"]) <= maxHeight:
                    continue
                maxHeight = int(ad_set["@maxHeight"])
                for cont in ad_set['ContentProtection']:
                    if '@schemeIdUri' not in cont:
                        continue
                    if cont['@schemeIdUri'].lower() == 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed':
                        pssh.append(cont['cenc:pssh'])
    else:
        for ad_set in periods['AdaptationSet']:
            if 'ContentProtection' not in ad_set:
                continue
            for cont in ad_set['ContentProtection']:
                if '@schemeIdUri' not in cont:
                    continue
                if cont['@schemeIdUri'].lower() == 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed':
                    pssh.append(cont['cenc:pssh'])
    return pssh[0] if pssh else None


def get_asin(url):
    a = url.split("/")
    if "dp" in a:
        return a[a.index("dp")+1]
    if "gp" in a:
        return a[a.index("gp")+1]
    return


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

    tld = "com"

    inp = input("ASIN / Prime Video Link: ")
    if inp.startswith("http"):
        print("The link will point towards the first episode if it's a season. "
              "Obtain the asin for each episode from the network tab.\n")
        a = urllib.parse.urlparse(inp).netloc.split(".")
        a.pop(0)
        a.pop(0)
        tld = '.'.join(a)
        asin = get_asin(inp)
    else:
        asin = inp

    auto_cookie = input("Get cookies from browser? (y/N): ").lower().startswith("y")

    if tld == "de":
        cookie_names = ["ubid-acbde", "x-acbde", "at-acbde"]
    elif tld == "co.uk":
        cookie_names = ["ubid-acbuk", "x-acbuk", "at-acbuk"]
    else:
        cookie_names = ["ubid-main", "x-main", "at-main"]

    if auto_cookie:
        try:
            ch = browser_cookie3.chrome()
        except Exception:
            print("\033[93mSkipping chrome for cookie retrieval since it is not closed.\033[0m")
            ch = None
        ff = browser_cookie3.firefox()

        for browser in [ch, ff]:
            if browser is None:
                continue
            values = (item in [cookie.name for cookie in browser if
                               (cookie.domain == f".amazon.{tld}" and not cookie.is_expired())] for item in
                      cookie_names)
            if all(values):
                cookies = {
                    cookie_names[0]: [cookie.value for cookie in browser if cookie.name == cookie_names[0]][0],
                    cookie_names[1]: [cookie.value for cookie in browser if cookie.name == cookie_names[1]][0],
                    cookie_names[2]: [cookie.value for cookie in browser if cookie.name == cookie_names[2]][0]
                }
                headers.cookies = cookies
                print("\033[92mSuccessfully retrieved cookies\033[0m")
    else:
        if not 'cookies' in headers.__dict__:
            print(f"\033[91mNo cookies found in headers.py\033[0m")
            sys.exit()
        if not all(item in headers.cookies for item in cookie_names):
            print(f"\033[91mMissing cookie names in headers.py\033[0m")
            sys.exit()
        if not all(len(headers.cookies[item]) > 0 for item in cookie_names):
            print(f"\033[91mMissing cookie values in headers.py\033[0m")
            sys.exit()

    j = get_playback_resources(asin)

    if 'error' in j:
        print("\033[91mUnable to get playback resources: \033[0m", end="")
        print(f"\033[91m{j['error']['errorCode']}\033[0m")
        if inp.startswith("http"):
            print(
                f"\033[91mCheck that the TLD country ({tld}) matches the TLD of the website you got the ASIN "
                f"from.\033[0m")
        if not auto_cookie:
            print("\033[91mCheck if your cookies match the website you got the ASIN from.\033[0m")
        sys.exit()

    catalog = j["catalogMetadata"]["catalog"]
    print("\n\033[93m" + catalog['title'] + "\033[0m")
    print("\033[90m" + catalog['synopsis'] + "\033[0m")

    if not input("Get keys? (y/N): ").lower().startswith("y"):
        sys.exit()

    try:
        urls = j["playbackUrls"]["urlSets"]
    except KeyError:
        print("No manifest urls found: ", end="")
        if 'rightsException' in j["returnedTitleRendition"]["selectedEntitlement"]:
            print(j["returnedTitleRendition"]["selectedEntitlement"]["rightsException"]["errorCode"])
        sys.exit()

    pssh = None
    mpd_url = None
    for u in urls:
        m = urls[u]["urls"]["manifest"]["url"]
        mpd_url = m
        mpd = requests.get(url=m)
        if mpd.status_code == 200:
            xml = xmltodict.parse(mpd.text)
            pssh = extract_pssh(xml)
            if pssh is not None:
                break

    if pssh is None:
        print("No PSSH found.")
        sys.exit()

    print(f"\n{mpd_url}\n")

    lic_url = (
            f"https://atv-ps{'' if tld is 'com' else '-eu'}.amazon.{tld}/cdp/catalog/GetPlaybackResources?deviceID=" +
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
