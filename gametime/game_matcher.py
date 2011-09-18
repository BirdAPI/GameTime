#!/usr/bin/python

import re

from IGN import ign
from IGN.ign import IGN
from IGN.ign import IGNInfo

from metacritic import metacritic
from metacritic.metacritic import Metacritic
from metacritic.metacritic import MetacriticInfo

from gamespot import gamespot
from gamespot.gamespot import Gamespot

from gametrailers import gametrailers
from gametrailers.gametrailers import GT, GTInfo


def match_to_metacritic(title, system):
    title_norm = normalize_game_title(title)
    system_norm = normalize_system(system)
    results = Metacritic.search(title, "game")
    for result in results:
        if normalize_system(result.system) == system_norm:
            if normalize_game_title(result.title) == title_norm:
                return result.id
    return None
    
def match_to_ign(title, system):
    title_norm = normalize_game_title(title)
    system_norm = normalize_system(system)
    results = IGN.search(title)
    for result in results:
        if normalize_system(result.system) == system_norm:
            if normalize_game_title(result.title) == title_norm:
                return result.id
    return None

def match_to_gamespot(title, system):
    title_norm = normalize_game_title(title)
    system_norm = normalize_system(system)
    results = Gamespot.search(title)
    for result in results:
        if normalize_system(result.system) == system_norm:
            if normalize_game_title(result.title) == title_norm:
                return result.id
    return None
    
def match_to_gametrailers(title, system):
    title_norm = normalize_game_title(title)
    system_norm = normalize_system(system)
    results = GT.search(title)
    for result in results:
        if normalize_system(result.system) == system_norm:
            if normalize_game_title(result.title) == title_norm:
                return result.id
    return None
    
def normalize_system(system):
    s = system.lower()
    if s in ["x360", "xbox 360", "xb360"]:
        return "Xbox 360"
    elif s in ["ps3", "playstation 3"]:
        return "PS3"
    elif s in ["wii"]:
        return "Wii"
    elif s in ["psp", "playstation portable"]:
        return "PSP"
    elif s in ["ds"]:
        return "DS"
    elif s in ["ps", "ps1", "playstation 1", "playstation1"]:
        return "PS1"
    elif s in ["ps2", "playstation 2", "playstation2"]:
        return "PS2"
    elif s in ["pc", "computer", "personal computer", "personalcomputer"]:
        return "PC"
    else:
        return system

def normalize_game_title(title):
    if not title:
        return None
    res = title
    replaces = { 
                ":" : "",
                "," : "",
                "\." : "",
                "_" : "",
                "-" : "",
                "\+" : "",
                " XIII( |$)" : "13",
                " VIII( |$)" : "8",
                " VII( |$)" : "7",
                " XII( |$)" : "12",
                " XIV( |$)" : "14",
                " XV( |$)" : "15",
                " III( |$)" : "3",
                " IV( |$)" : "4",
                " V( |$)" : "5",
                " VI( |$)" : "6",
                " II( |$)" : "2",
                " IX( |$)" : "9",
                " XI( |$)" : "11",
                " X( |$)" : "10",
                "(^T| t)he " : "",
                " of " : "",
                " and " : "",
                " a " : "",
                "A " : "",
                "'" : ""
               }
    for (key, value) in replaces.items():
        res = re.sub(key, value, res)
    res = res.replace(" ", "").lower()
    print title, "->", res
    return res
