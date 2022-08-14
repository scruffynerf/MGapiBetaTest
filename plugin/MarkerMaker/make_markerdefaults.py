# Enable or disable the plugin (use the task buttons inside Stash)
enable_marker_hook = False
# Marker
# If you want to create a marker while Scraping.
CREATE_MARKER = True
# Only create marker if the durations match (API vs Stash)
MARKER_DURATION_MATCH = False
# Sometimes the API duration is 0/1, so we can't really know if this matches. True if you want to create anyways
MARKER_DURATION_UNSURE = True
# Max allowed difference (seconds) in scene length between Stash & API.
MARKER_SEC_DIFF = 2000
#
MARKER_PATH = "/tmp"

