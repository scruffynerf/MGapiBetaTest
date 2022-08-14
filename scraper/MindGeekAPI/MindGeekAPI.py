import json
import os
import re
import sys
import difflib 
from datetime import datetime 
from urllib.parse import urlparse

try:
    import requests
except ModuleNotFoundError:
    print("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)", file = sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests", file = sys.stderr)
    sys.exit()

# if you put this into a subdirectory of scrapers, and pycommon is in scraper
sys.path.insert(0, '..')

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file = sys.stderr)
    sys.exit()

# first time run, setup config.py
if not os.path.exists("config.py"):
    with open("MindGeekAPIdefaults.py", 'r') as default:
        config_lines = default.readlines()
    with open("config.py", 'w') as firstrun:
        firstrun.write("from MindGeekAPIdefaults import *\n")
        for line in config_lines:
            if not line.startswith("##"):
                firstrun.write(f"#{line}")

import config

# network stuff
def sendRequest(url, head): 
    #log.debug( f"Request URL: {url}")
    try:
        response = requests.get(url, headers = head, timeout = 10, verify = config.CHECK_SSL_CERT)
    except requests.exceptions.SSLError:
        log.error("SSL Error on this site. You can ignore this error with the 'CHECK_SSL_CERT' param inside the python file.")
        return None
    # log.debug( f"Returned URL: {response.url}")
    if response.content and response.status_code == 200:
        return response
    else:
        log.error( f"[REQUEST] Error, Status Code: {response.status_code}")
        if response.status_code == 429:
            log.error("[REQUEST] 429 Too Many Requests, You have sent too many requests in a given amount of time.")
        return None

# Config tools

def configfile_edit(configfile, name: str, state: str):
    found = 0
    with open(configfile, 'r') as file:
        config_lines = file.readlines()
    with open(configfile, 'w') as file_w:
        for line in config_lines:
            if name == line.split("=")[0].strip():
                file_w.write(f"{name} = {state}\n")
                found += 1
            elif "#" + name == line.split("=")[0].strip():
                file_w.write(f"{name} = {state}\n")
                found += 1
            else:
                file_w.write(line)
        if not found:
            file_w.write( f"{name} = {state}\n")
            found = 1
    return found

def check_config(domain):
    try:
        if getattr(config, domain + '_date') is None:
            return None
        #getattr(config, 'domain_date') is the same as config.domain_date
        config_date = datetime.strptime(getattr(config, domain + '_date'), '%Y-%m-%d')
        date_diff = datetime.strptime(DATE_TODAY, '%Y-%m-%d') - config_date
        if date_diff.days == 0: #date is within 24 hours so using old instance
            token = getattr(config, domain + '_instance')
            # log.debug(token)
            return token
        else: 
            #log.debug("Old Config date: {}".format(config_date))
            pass
    except: 
        #log.debug("no such domain")
        pass
    return None

def write_config(url, token): 
    #log.debug("Writing config!")
    domain = re.sub(r"www\.|\.com", "", urlparse(url).netloc)
    domain
    if domain not in config.domains:
        config.domains.append(domain)
    configfile_edit(config.__file__, "domains", str(config.domains))
    # log.debug("domains written")
    configfile_edit(config.__file__, domain + '_url', '"{}"'.format(url))
    # log.debug("url written")
    configfile_edit(config.__file__, domain + '_searchable', 'True')
    # log.debug("domain search enabled")
    configfile_edit(config.__file__, domain + '_instance', '"{}"'.format(token))
    # log.debug("instance written")
    configfile_edit(config.__file__, domain + '_date', '"{}"'.format(DATE_TODAY))
    # log.debug("date written")
    return

# API
def api_token_get(url): #API TOKEN
    domain = re.sub(r"www\.|\.com", "", urlparse(url).netloc)
    api_token = check_config(domain)
    if api_token is None:
        log.info("Need to get API Token")
        r = sendRequest(url, {'User-Agent': config.USER_AGENT})
        if r:
            api_token = r.cookies.get_dict().get("instance_token")
            if api_token is None:
                log.error("Can't get the instance_token from the cookie.")
                sys.exit(1)
        # Writing new token in the config file
        write_config(url, api_token)
        # log.debug("Token: {}".format(api_token))
    api_headers = {
        'Instance': api_token,
        'User-Agent': config.USER_AGENT,
        'Origin': 'https://' + urlparse(url)
            .netloc,
        'Referer': url
    }
    return api_headers


def url_process():
    global SCENE_URL
    global SCENE_ID 
    
    # fixing old scene
    if 'brazzers.com/scenes/view/id/' in SCENE_URL:
        log.info("Probably an old url, need to redirect")
        try:
            r = requests.get(SCENE_URL, headers = {'User-Agent': config.USER_AGENT}, timeout = (3, 5))
            SCENE_URL = r.url
        except:
            log.warning("Redirect failed, result may be inaccurate.")# extract thing
    domain = re.sub(r"www\.|\.com", "", urlparse(SCENE_URL).netloc)
    # log.debug("Domain: {}".format(domain))
    if domain not in config.domains: 
        #we don't have the domain yet, so lets' try using the home page, before we worry about scene
        url_home = f"https://www.{domain}.com"
        # log.debug( f"Fetching API token from main page:{url_home}")
        api_headers = api_token_get(url_home)
        # if api_headers: #log.debug( f"Fetched, site in domains now hopefully")
    url_check = re.sub('.+/', '', SCENE_URL)
    try:
        if url_check.isdigit():
            url_sceneid = url_check
        else:
            url_sceneid = re.search(r"/(\d+)/*", SCENE_URL).group(1)
    except:
        url_sceneid = None
    if url_sceneid is None:
        log.error("Can't get the ID of the Scene. Are you sure that URL is from a site in the Mindgeek Network?")
        sys.exit()
    
    log.debug("ID: {}".format(url_sceneid))

    # API ACCESS
    api_headers = api_token_get(SCENE_URL)
    api_URL = 'https://site-api.project1service.com/v2/releases/{}'.format(url_sceneid)

    # EXPLORE API
    api_scene_json = sendRequest(api_URL, api_headers)
    try:
        if type(api_scene_json.json()) == list:
            api_scene_json = api_scene_json.json()[0].get('message')
            log.error("API Error Message: {}".format(api_scene_json))
            sys.exit(1)
        else:
            api_scene_json = api_scene_json.json().get('result')
    except:
        log.error("Failed to get the JSON from API")
        local_tmp_path = os.path.join(JSON_PATH, url_sceneid + ".json")
        if os.path.exists(local_tmp_path):
            log.info("Using local file ({})".format(url_sceneid + ".json"))
        else:
            local_tmp_path = os.path.join(JSON_PATH, url_sceneid + "_MG.json")
            if os.path.exists(local_tmp_path):
                log.info("Using local file ({})".format(url_sceneid + "_MG.json"))
            else:
                log.error("error, no local json file either")
                sys.exit(1)
        with open(local_tmp_path, "r", encoding = "utf8") as file:
            api_scene_json = json.load(file)

    if api_scene_json:
        if api_scene_json.get('parent') is not None and api_scene_json['type'] != "scene":
            if api_scene_json['parent']['type'] == "scene":
                api_scene_json = api_scene_json.get('parent')
        scraped_json = scraping_json(api_scene_json, SCENE_URL)
    else:
        scraped_json = None
    return scraped_json

def title_process():
    global SCENE_TITLE

    # log.debug("processing title")

    SCENE_TITLE = re.sub(r'[-._\']', ' ', os.path.splitext(SCENE_TITLE)[0])# Remove resolution
    SCENE_TITLE = re.sub(r'\sXXX|\s1080p|720p|2160p|KTR|RARBG|\scom\s|\[|]|\sHD|\sSD|', '', SCENE_TITLE)# Remove Date
    SCENE_TITLE = re.sub(r'\s\d{2}\s\d{2}\s\d{2}|\s\d{4}\s\d{2}\s\d{2}', '', SCENE_TITLE)

    # log.debug("Title: {}".format(SCENE_TITLE))

    # Reading config
    if config.domains is None:
        log.error("Can't search yet, you need to scrape a URL from the domain/network, to enable searching.")
    sys.exit(1)

    # Loop the config
    scraped_json = None
    ratio_record = 0
    for domain in config.domains:
        if getattr(config, domain + '_searchable') == False:
            log.debug("NOT Searching on: {}".format(domain))
            continue
        log.info("Searching on: {}".format(domain))

        # API ACCESS
        config_url = getattr(config, domain + '_url')
        api_headers = api_token_get(config_url)
        search_url = 'https://site-api.project1service.com/v2/releases?title={}&type=scene'.format(SCENE_TITLE)
        api_search_json = sendRequest(search_url, api_headers)
        try:
            if type(api_search_json.json()) == list:
                api_search_error = api_search_json.json()[0]['message']
                log.error("API Error Message: {}".format(api_search_error))
                continue
            else:
                api_search_json = api_search_json.json()['result']
        except:
            log.error("Failed to get the JSON from API")
            continue

        ratio_scene = None
        making_url = None
        for result in api_search_json:
            title_filename = None
            try:
                api_filename = result['videos']['mediabook']['files']["320p"]['urls']['download']
                title_filename = re.sub(r'^.+filename=', '', api_filename)
                title_filename = re.sub(r'_.+$', '', title_filename)
            except:
                pass
        
            if title_filename:
                making_url = re.sub(r'/\d+/*.+', '/' + str(result.get("id")) + "/" + title_filename, config_url)
            else:
                making_url = re.sub(r'/\d+/*.+', '/' + str(result.get("id")) + "/", config_url)
            
            ratio = round(difflib.SequenceMatcher(None, SCENE_TITLE.lower(), result["title"].lower()).ratio(), 3)
            # log.debug("[MATCH] Title: {} | Ratio: {}".format(result.get('title'), ratio))
            if ratio > ratio_record:
                ratio_record = ratio
                ratio_scene = result
        if ratio_record > config.SET_RATIO:
            log.info("Found scene {}".format(ratio_scene["title"]))
            scraped_json = scraping_json(ratio_scene, making_url)
            break
    if scraped_json is None:
        log.error("API Search Error. No scenes found")
        sys.exit(1)

    return scraped_json

def title_search():
    if config.domains is None:
        log.error("Can't search for the scene ({} is missing) You need to scrape 1 URL from the network, to be enable to search with your title on this network.".format(config_file_used))
        sys.exit(1)

    # Loop the config

    scraped_json = None
    result_search = []
    searchcount = 0
    disabled_domains = []
    
    for domain in config.domains:
        try:
            #log.debug(getattr(config, domain + '_searchable'))
            if getattr(config, domain + '_searchable') == False:
               disabled_domains.append(domain)
               #log.info("Searching disabled on: {}".format(domain))
               continue
        except:
            # if we got here, we didn't have a _searchable attribute, let's add one
            configfile_edit(config.__file__,domain + '_searchable', 'False')
            #log.debug(f"{domain} search enable not found, added and disabled by default")

        #log.info("Searching on: {}".format(domain))
        match_filter = re.match(r"{.+}", SEARCH_TITLE.lower())
        if match_filter:
            filter_domain = re.sub(r"[{}]","", match_filter.group(0))
            filter_domain = filter_domain.split(",")
            if domain not in filter_domain:
                log.info("Ignoring {} (Filter query)".format(domain))
                continue
        match_filter = re.match(r"!.+!", SEARCH_TITLE.lower())
        if match_filter:
            filter_domain = re.sub(r"[!!]","", match_filter.group(0))
            filter_domain = filter_domain.split(",")
            if domain in filter_domain:
                log.info("Ignoring {} (Filter query)".format(domain))
                continue
        log.info("Searching on: {}".format(domain))
        
        # API ACCESS
        try:
            config_url = getattr(config, domain + '_url')
        except:
            # if we got here, we didn't have a _url attribute, so let's add the site url alone, better than no url
            config_url = f"https://www.{domain}.com"
            configfile_edit(config.__file__,domain + '_url', config_url)
            #log.debug(f"{domain} missing, trying site url alone")
        
        api_headers = api_token_get(config_url)
        search_url = 'https://site-api.project1service.com/v2/releases?title={}&type=scene&limit=20'.format(re.sub(r"{.+}\s*", "", SEARCH_TITLE))
        api_search_json = sendRequest(search_url, api_headers)
        if api_search_json is None:
            log.error("Request fail")
            continue
        try:
            if type(api_search_json.json()) == list:
                api_search_error = api_search_json.json()[0]['message']
                log.error("API Error Message: {}".format(api_search_error))
                continue
            else:
                api_search_json = api_search_json.json()['result']
        except:
            log.error("Failed to get the JSON from API ({})".format(domain))
            continue

        ratio_scene = None
        making_url = None
        ratio_record = 0

        for result in api_search_json:
            search = {}
            try:
                result['collections'][0].get('name') # If this create a error it wont continue so no studio at all
                search['studio'] = {}
                search['studio']['name'] = result['collections'][0].get('name')
            except:
                try:
                    result['brandMeta'].get('displayName') # If this create a error it wont continue so no studio at all
                    search['studio'] = {}
                    search['studio']['name'] = result['brandMeta'].get('displayName')
                except:
                    log.warning("No studio")
                    #log.debug(result)

            search['title'] = result.get('title')

            searchmatch = search['title'] + " "
            for name in result.get('actors'):
                searchmatch = searchmatch + " " + name.get('name')
            
            ratio1 = round(difflib.SequenceMatcher(None, SEARCH_TITLE.lower(), searchmatch.lower()).ratio(), 3)
            ratio2 = round(difflib.SequenceMatcher(None, SEARCH_TITLE.lower(), search['title'].lower()).ratio(), 3)
            ratio = max(ratio1, ratio2)
            #log.debug("[MATCH] Title: {} | Ratio: {}".format(search['title'], ratio))
            #log.info("Found scene {}".format(search['title']))
            search["ratio"] = ratio
            search['searchsource'] = domain

            title_filename = None
            try:
                api_filename = result['videos']['mediabook']['files']["320p"]['urls']['download']
                title_filename = re.sub(r'^.+filename=', '', api_filename)
                title_filename = re.sub(r'_.+$', '', title_filename)
            except:
                pass

            if title_filename:
                making_url = re.sub(r'/\d+/*.+', '/' + str(result.get("id")) + "/" + title_filename, config_url)
            else:
                making_url = re.sub(r'/\d+/*.+', '/' + str(result.get("id")) + "/", config_url)

            try:
                search['image'] = result['images']['poster']['0']["xl"]['url']
            except:
                pass

            try:
                search['performers'] = [{"name": x.get('name')} for x in result.get('actors')]
            except:
                pass

            search['url'] = making_url

            result_search.append(search)
            searchcount += 1
        if searchcount >= 50:
            # Try to to avoid more than 50ish results, Stash dislikes more
            break

    #log.debug(f"search finishing, collating {searchcount} entries")
    if searchcount == 0:
        log.error("API Search Error. No scenes found")
        log.info(f"You might want to enable searching on some of these: {disabled_domains}")

        #scraped_json = {"title":"No scenes found. (Hover to see everything)"}
        #scraped_json["details"] = """

        #To add a site into the scraper config, you need to scrape _1_ url from that site first.
        #Example: get a url from Brazzers -> use 'Scrape With... MindGeekAPI 2.0' -> now you can search on Brazzers.
        #Filter your search with \{site\} query or !site! query' Multiple site filtering: use commas {brazzers,milehighmedia}.
        #Use ! to NOT search some sites: !brazzers,milehighmedia! (site = domain without www/com)
        #Available sites are shown in the tags."""
        #scraped_json['tags'] = [{"name": x} for x in config.domains]
        #scraped_json = [scraped_json]
    else:
        if searchcount >= 50:
            log.error("API Search Error. Too many scenes found")
        #log.debug("results pre sort")
        #log.debug(result_search)
        imageurlseen = []
        scraped_json = []
        result_search.sort(key=lambda x: x["ratio"], reverse=True)
        log.debug(result_search)
        for item in result_search:
            if not any(chr.isdigit() for chr in item['url']):
                #log.debug(f"{item['title']} removing due to bad url - {item['url']}")
                log.error (f"{item.pop('searchsource')} needs a real scene url in config to return real url results")
                continue
            if item['image'] in imageurlseen:
                #log.debug("duplicate image, duplicate scene")
                continue
            else:
                imageurlseen.append(item['image'])
                #log.debug(imageurlseen)
                item.pop('ratio')
                item.pop('searchsource')
                scraped_json.append(item)         
        #log.debug("results post sort")
        #log.debug(scraped_json)
    return scraped_json    
  
#def toomany():
#    scraped_json = {}
#    scraped_json["title"] = "Too many scenes found. Hover to see everything"
#    scraped_json["details"] = """Filter your search down a bit: use '{site} query' to limit OR '!site! query' to avoid.
#Available sites are shown in the tags. Use site,site for multiples"""
#    scraped_json['tags'] = [{"name": x} for x in config.domains]
#    #scraped_jason = json.dumps(scraped_json)
#    #log.debug(scraped_json)
#    return scraped_json

#def noresults():
#    scraped_json = {}
#    scraped_json["title"] = "No scenes found. Hover to see everything"
#    scraped_json["details"] = """Change your search terms: use '{site} query' to limit OR '!site! query' to avoid.
#Available sites are shown in the tags. Use site,site for multiples"""
#    scraped_json['tags'] = [{"name": x} for x in config.domains]
#    return [scraped_json]

# Final scraping
def scraping_json(api_json, url=""):
    global SCENE_ID
    MakeMarkerTag = False
    scrape = {}

    scrape['title'] = api_json.get('title')

    date = datetime.strptime(api_json.get('dateReleased'), '%Y-%m-%dT%H:%M:%S%z')
    scrape['date'] = str(date.date())

    scrape['details'] = api_json.get('description')

    # URL
    if url:
        scrape['url'] = url
    else:
        scrape['url'] = f"https://www.{api_json.get('brand')}.com/video/{api_json.get('id')}/scene"

    # Studio
    try:
        api_json['collections'][0].get('name') # If this creates an error it wont continue so no studio at all
        scrape['studio'] = {}
        scrape['studio']['name'] = api_json['collections'][0].get('name')
    except:
        log.warning("No studio")

    # Performers
    if config.female_only:
        perf = []
        for x in api_json.get('actors'):
            if x.get('gender') == "female":
                perf.append({"name": x.get('name'), "gender": x.get('gender')})
        scrape['performers'] = perf
    else:
        scrape['performers'] = [{"name": x.get('name'), "gender": x.get('gender')} for x in api_json.get('actors')]

    # Image can be poster or poster_fallback
    backup_image=None
    if type(api_json['images']['poster']) is list:
        for image_type in api_json['images']['poster']:
            try:
                if '/poster_fallback/' in image_type['xx'].get('url') and backup_image is None:
                    backup_image = image_type['xx'].get('url')
                    continue
                if '/poster/' in image_type['xx'].get('url'):
                    scrape['image'] = image_type['xx'].get('url')
                    break
            except TypeError:
                pass
    else:
        if type(api_json['images']['poster']) is dict:
            for _, img_value in api_json['images']['poster'].items():
                try:
                    if '/poster_fallback/' in img_value['xx'].get('url') and backup_image is None:
                        backup_image = img_value['xx'].get('url')
                        continue
                    if '/poster/' in img_value['xx'].get('url'):
                        scrape['image'] = img_value['xx'].get('url')
                        break
                except TypeError:
                    pass

    if scrape.get('image') is None and backup_image:
        log.info("Using alternate image")
        scrape['image'] = backup_image

    if config.SAVE_JSON:
        if SCENE_ID:
            local_save_path = os.path.join(config.JSON_PATH,"scene" + str(SCENE_ID) + "_MG.json")
        else:
            local_save_path = os.path.join(config.JSON_PATH,"id" + str(api_json.get('id')) + "_MG.json")
        log.info(f"Saving json as ({local_save_path})")
        with open(local_save_path, 'w') as jsonfile:
            jsonfile.write(json.dumps(api_json))

    if config.CREATE_MARKER:        
        if api_json.get("timeTags"):
            MakeMarkerTag = True
            markercount = len(api_json.get("timeTags"))
            log.info(f"{markercount} offical markers found for this scene")
            if SCENE_ID:
                local_save_path = os.path.join(config.MARKER_PATH,"scene" + str(SCENE_ID) + "_markers.json")
            else:
                local_save_path = os.path.join(config.MARKER_PATH,"id" + str(api_json.get('id')) + "_markers.json")
            log.info(f"Saving local file for making markers: ({local_save_path})")
            with open(local_save_path, 'w') as markerfile:
                markerfile.write(json.dumps(api_json))
                # we'll handle this on Scene Update, meaning we've saved this scene, and we will remove Make Marker tags then.               
        else:
            log.info("No offical markers for this scene")
    
    # tags
    list_tag = []
    for x in api_json.get('tags'):
        tag_name = x.get('name')
        if tag_name in config.IGNORE_TAGS:
            continue
        if tag_name:
            list_tag.append({"name": x.get('name')})
    if config.FIXED_TAGS:
        for f in config.FIXED_TAGS:
            list_tag.append({"name": f})
    if MakeMarkerTag:
        list_tag.append({"name": 'MakeMarkersOnSave'})
        list_tag.append({"name": 'Markers:'+str(markercount)})
    scrape['tags'] = list_tag

    return scrape

#begin main code

DATE_TODAY = datetime.today().strftime('%Y-%m-%d')
FRAGMENT = json.loads(sys.stdin.read())
#log.debug(FRAGMENT)

SEARCH_TITLE = FRAGMENT.get("name")
SCENE_TITLE = FRAGMENT.get("title")
SCENE_URL = FRAGMENT.get("url")

# unfortunately, we don't always get passed a scene id, we can't count on this
SCENE_ID = FRAGMENT.get("id")

scraped_json = None

if "validName" in sys.argv and SCENE_URL is None:
    sys.exit()

if SCENE_URL:
    # url is best
    scraped_json = url_process()
elif SCENE_TITLE:
    # full title is second best
    scraped_json = title_process()
elif SEARCH_TITLE:
    # partial title/search is 3rd choice
    scraped_json = title_search()

print(json.dumps(scraped_json))
