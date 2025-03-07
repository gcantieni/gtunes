# ===============
# General helpers
# ===============

# Accept timestamps in the format 1:30 where 1 is the minutes and 30 is the seconds
def timestamp_to_seconds(timestamp):
    sum(x * int(t) for x, t in zip([60, 1], timestamp.split(":")))