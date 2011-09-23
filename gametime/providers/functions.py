from pprint import pprint
import constants
import re

def try_get_attr(obj, *attr_names):
    for attr in attr_names:
        try:
            return obj.__dict__[attr]
        except KeyError:
            pass
    return None

def normalize_system(system):
    if not system:
        return None
    s = system.lower().replace("-", "").replace("_", "")
    for key, value in constants.SYSTEM_ALIASES.items():
        for v in value:
            regex = "^{0}$".format(v)
            if re.match(regex, s):
                return key
    return system

def is_game_match(title, system, release_str):
    norm_title = normalize_game_title(title)
    system_matches = find_system_in_string(release_str)
    for sysname, match_str in system_matches:
        if sysname == system:
            s = release_str[:release_str.lower().find(match_str)]
            if norm_title == normalize_game_title(s):
                return True
    if len(system_matches) == 0:
        region_matches = find_regions_in_string(release_str)
        for regname, match_str in region_matches:
            s = release_str[:release_str.upper().find(match_str)]
            if norm_title == normalize_game_title(s):
                return True
    return False

"""
Attempts to find a system inside of a string (presumably a release title)
Returns the normalized system if found, or None if not found
"""    
def find_system_in_string(string):
    possible_matches = []
    s = string.lower()
    for key, value in constants.SYSTEM_ALIASES.items():
        for v in value:
            regex = "([\. _\-]|^)(?P<system>{0})([\. _\-]|$)".format(v)
            match = re.search(regex, s)
            if match:
                possible_matches.append((key, match.group(0)))
    return possible_matches

def find_regions_in_string(string):
    possible_matches = []
    s = string.upper()
    for region in constants.REGIONS:
        regex = "([\. _\-]|^)(?P<region>{0})([\. _\-]|$)".format(region.replace(" ?", "[\. _\-]?"))
        match = re.search(regex, s)
        if match:
            possible_matches.append((region, match.group(0)))
    return possible_matches

def normalize_game_title(title, echo=False):
    if not title:
        return None
    res = title
    for key, value in constants.TITLE_REPLACES.items():
        res = re.sub(key, value, res)
    res = replace_roman_numerals(res)
    res = res.replace(" ", "").lower()
    if echo:
        print title, "->", res
    return res

def replace_roman_numerals(title):
    res = title.upper()
    for key, value in constants.ROMAN_NUMERALS.items():
        regex = "( |^){0}( |$)".format(key)
        res = re.sub(regex, value, res)
    return res

def main():
    print normalize_system("Nintendo DS")
    print normalize_system("XBLA")
    print normalize_system("Super Nintendo")
    print normalize_system("PlayStation 3")
    print ""
    print replace_roman_numerals("XIII")
    print replace_roman_numerals("XIX")
    print ""
    print normalize_game_title("Fable III")
    print normalize_game_title("Disgaea 4: A Promise Unforgotten")
    print ""
    pprint(find_system_in_string("F1.2011.X360-COMPLEX"))
    pprint(find_system_in_string("[NEW] Disgaea 4 USA iMARS"))
    pprint(find_system_in_string("ICO.and.Shadow.of.the.Colossus.PS3-DUPLEX"))
    print ""
    print is_game_match("F1 2011", "Xbox 360", "F1 2011 XBOX360 COMPLEX")
    print is_game_match("Disgaea 4", "PS3", "Disgaea 4 USA iMARS")
    print is_game_match("The ICO and Shadow of the Colossus Collection", "PS3", "ICO.and.Shadow.of.the.Colossus.PS3-DUPLEX")

if __name__ == "__main__":
    main()
