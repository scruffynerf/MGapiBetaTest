import os
import sys
import json

try:
    import stashapi.log as log
    import stashapi.marker_parse as mp
    from stashapi.tools import human_bytes
    from stashapi.types import PhashDistance
    from stashapi.stashapp import StashInterface
except ModuleNotFoundError:
    print("You need to install the stashapp-tools (stashapi) python module. (CLI: pip install stashapp-tools)", file=sys.stderr)

#cwd = os.getcwd()
os.chdir(os.path.dirname(os.path.realpath(__file__)))
#cwd = os.getcwd()
#log.debug(f"The current directory is: {cwd}")

if not os.path.exists("config.py"):
    with open("make_markerdefaults.py", 'r') as default:
        config_lines = default.readlines()
    with open("config.py", 'w') as firstrun:
        firstrun.write("from make_markerdefaults import *\n")
        for line in config_lines:
            if not line.startswith("##"):
                firstrun.write(f"#{line}")

import config

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
            file_w.write(f"#\n{name} = {state}\n")
            found = 1
    return found

def exit_plugin(msg=None, err=None):
    if msg is None and err is None:
        msg = "plugin ended"
    output_json = {"output": msg, "error": err}
    print(json.dumps(output_json))
    sys.exit()

def basename(f):
    f = os.path.normpath(f)
    return os.path.basename(f)

def getSceneTitle(scene):
    if scene["title"] != None and scene["title"] != "":
        return scene["title"]
    return basename(scene["path"])

def getGenreTags():
    query = """
    {
      findTags(
        tag_filter: {name: {value: """ + '"' + config.genre_parentname + '"' + """ , modifier: EQUALS}}
        filter: {per_page: -1}
      ) {
        count
        tags {
          id
          name
          children {
            name
            id
          }
        }
      }
    }
    """
    results = stash.graphql_query(query)
    resultschildren = results["findTags"]["tags"][0]["children"]
    return get_ids(resultschildren)

def get_ids(obj):
    ids = []
    for item in obj:
        ids.append(item['id'])
    return ids

def writeFile(fn, data, useUTF=False):
    encoding = None
    if useUTF:
        encoding = "utf-8-sig"
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    f = open(fn, "w", encoding=encoding)
    f.write(data)
    f.close()
    
def marker_load_file(scene):
    #log.debug(scene)
    if os.path.exists("config.py"):
        scene_id = scene["id"]
        file_path = os.path.join(config.MARKER_PATH,"scene" + str(scene_id) + "_markers.json")
        if not os.path.exists(file_path):
            #mg_id = something
            file_path = os.path.join(config.MARKER_PATH,"id" + str(mg_id) + "_markers.json")
            if not os.path.exists(file_path):
                log.error("Can't find file to load")
                sys.exit()
    log.info(f"Reading marker file: ({file_path})")
    with open(file_path, 'r') as markerfile:
        marker_json = markerfile.read()
    timetags = json.loads(marker_json).get('timeTags')
    #log.debug(timetags)
    markers = []
    for item in timetags:
        # desired marker format:
    	#   "seconds": <int>, <float>, <string> value parseable to float (REQUIRED)
    	#   "primary_tag": <string> tag name (REQUIRED)
    	#   "tags": [<string> tag name]
    	#   "title": <string> title of marker
        # timetag format {"id": #, "name": tagname, "startTime": #, "endTime": #}
        marker = {}
        marker["seconds"] = item["startTime"]
        marker["primary_tag"] = item["name"]
        marker["tags"] = []
        marker["title"] = f"{item['name']}"
        markers.append(marker)
    #log.debug(markers)
    return markers

def marker_save():
    return None
    #for marker in api_json["timeTags"]:
    #    if stash_scene_info.get("marker"):
    #        if marker.get("startTime") in stash_scene_info["marker"]:
    #            log.debug("Ignoring marker ({}) because already have with same time.".format(marker.get("startTime")))
    #            continue
    #    try:
    #        graphql_createMarker(SCENE_ID, marker.get("name"), marker.get("name"), marker.get("startTime"))
    #    except:
    #        log.error("Marker failed to create")

    #markercount = 0
    #for marker in api_json["timeTags"]:
    #  if stash_scene_info.get("marker"):
    #       if marker.get("startTime") in stash_scene_info["marker"]:
    #          log.debug("Ignoring marker ({}) because already have with same time.".format(marker.get("startTime")))
    #           continue
    #      markerfile.write("{}_{} = {}\n".format(marker_count, marker.get("name"), marker.get("startTime")))
    #      markercount += 1



    #        stash_scene_info = st.graphql_getScene(SCENE_ID)
    #        api_scene_duration = None
    #        if api_json.get("videos"):
    #            if api_json["videos"].get("mediabook"):
    #                api_scene_duration = api_json["videos"]["mediabook"].get("length")
    #        if config.MARKER_DURATION_MATCH and api_scene_duration is None:
    #            log.info("No duration given by the API.")
    #        else:
    #            timediff = abs(stash_scene_info["duration"] - api_scene_duration)
    #            log.debug("Stash Len: {}| API Len: {}| difference is {} secs".format(stash_scene_info["duration"], api_scene_duration,timediff))
    #            if (   config.MARKER_DURATION_MATCH 
    #                or timediff <= int(config.MARKER_SEC_DIFF)
    #                or (api_scene_duration in [0,1] and config.MARKER_DURATION_UNSURE)):
    #set the tag to make markers here
    #                   MakeMarkerTag = True
    #                   local_tmp_path = os.path.join(config.TMPPATH,SCENE_ID + "_markers.json")
       
    #            else:
    #                       log.info("The duration of this scene doesn't match the duration of stash scene closely enough.")
                                       

def main():
    global stash
    json_input = json.loads(sys.stdin.read())
    #log.debug(json_input)
    FRAGMENT_SERVER = json_input["server_connection"]
    stash = StashInterface(FRAGMENT_SERVER)
    PLUGIN_ARGS = False
    HOOKCONTEXT = False

    try:
        PLUGIN_ARGS = json_input['args']["mode"]
        #log.debug(PLUGIN_ARGS)
    except:
        pass

    if PLUGIN_ARGS:
        log.debug("--Starting Plugin 'Marker Maker'--")
        if "enable" in PLUGIN_ARGS:
            log.info("Enable Marker Maker hook")
            success = configfile_edit("config.py", "enable_marker_hook", "True")
        elif "disable" in PLUGIN_ARGS:
            log.info("Disable Marker Maker hook")
            success = configfile_edit("config.py", "enable_marker_hook", "False")
        if not success:
            log.error("Script failed to change the value of 'enable_marker_hook' variable")
        exit_plugin("Marker Maker script finished")

    try:
        HOOKCONTEXT = json_input['args']["hookContext"]
    except:
        exit_plugin("Marker Maker hook: No hook context")

    if not config.enable_marker_hook:
        exit_plugin("Marker Maker Hook disabled")
    else:
        log.debug("--Starting Hook 'Marker Maker Exporter'--")

    sceneID = HOOKCONTEXT['id']
    scene = stash.find_scene(sceneID)
    current_markers = scene.get("scene_markers")
    log.debug(current_markers)
    markers = marker_load_file(scene)
    #log.debug(markers)
    #markers.sort(key=lambda x: x["endTime"], reverse=True)
    #log.debug(markers)
    for marker in markers:
        log.debug(marker)
    mp.import_scene_markers(stash, markers, sceneID, 15)


main()
