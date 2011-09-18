import ign_provider as ign
import gamespot_provider as gamespot
import gametrailers_provider as gametrailers
import metacritic_provider as metacritic

GAME_PROVIDERS = {}

IGN_PROVIDER = ign.provider
GAME_PROVIDERS[IGN_PROVIDER.site_id] = IGN_PROVIDER

GAMESPOT_PROVIDER = gamespot.provider
GAME_PROVIDERS[GAMESPOT_PROVIDER.site_id] = GAMESPOT_PROVIDER

GT_PROVIDER = gametrailers.provider
GAME_PROVIDERS[GT_PROVIDER.site_id] = GT_PROVIDER

METACRITIC_PROVIDER = metacritic.provider
GAME_PROVIDERS[METACRITIC_PROVIDER.site_id] = METACRITIC_PROVIDER

