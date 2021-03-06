# -*- coding: utf-8 -*-

#from builtins import str
import sys

from core.support import typo

PY3 = False
if sys.version_info[0] >= 3: PY3 = True; unicode = str; unichr = chr; long = int

import xbmc, os, traceback

from channelselector import get_thumb, thumb
from core import filetools
from core import scrapertools
from core import videolibrarytools
from core.item import Item
from platformcode import config, logger
from platformcode import platformtools
from lib import generictools
from distutils import dir_util


def mainlist(item):
    logger.info()

    itemlist = list()
    itemlist.append(Item(channel=item.channel, action="list_movies", title=config.get_localized_string(60509),
                         category=config.get_localized_string(70270),
                         thumbnail=get_thumb("videolibrary_movie.png")))
    itemlist.append(Item(channel=item.channel, action="list_tvshows", title=config.get_localized_string(60600),
                         category=config.get_localized_string(70271),
                         thumbnail=get_thumb("videolibrary_tvshow.png")))
    itemlist.append(Item(channel='shortcuts', action="SettingOnPosition",
                         category=2, setting=1, title=typo(config.get_localized_string(70287),'bold color kod'),
                         thumbnail = get_thumb("setting_0.png")))

    return itemlist


def channel_config(item):
    return platformtools.show_channel_settings(channelpath=os.path.join(config.get_runtime_path(), "channels", item.channel), caption=config.get_localized_string(60598))


def list_movies(item, silent=False):
    logger.info()
    itemlist = []
    dead_list = []
    zombie_list = []
    for raiz, subcarpetas, ficheros in filetools.walk(videolibrarytools.MOVIES_PATH):
        for s in subcarpetas:
            nfo_path = filetools.join(raiz, s, s + ".nfo")
            logger.debug(nfo_path)

            local_movie = False
            for f in filetools.listdir(filetools.join(raiz, s)):
                if f.split('.')[-1] not in ['nfo','json','strm']:
                    local_movie = True
                    break

            if filetools.exists(nfo_path):
                # We synchronize the movies seen from the Kodi video library with that of KoD
                try:
                    # If it's Kodi, we do it
                    if config.is_xbmc():
                        from platformcode import xbmc_videolibrary
                        xbmc_videolibrary.mark_content_as_watched_on_kod(nfo_path)
                except:
                    logger.error(traceback.format_exc())

                head_nfo, new_item = videolibrarytools.read_nfo(nfo_path)

                # If you have not read the .nfo well, we will proceed to the next
                if not new_item:
                    logger.error('.nfo erroneous in ' + str(nfo_path))
                    continue

                if len(new_item.library_urls) > 1:
                    multicanal = True
                else:
                    multicanal = False

                # Verify the existence of the channels. If the channel does not exist, ask yourself if you want to remove the links from that channel.

                for canal_org in new_item.library_urls:
                    canal = generictools.verify_channel(canal_org)
                    try:
                        if canal in ['community', 'downloads']:
                            channel_verify = __import__('specials.%s' % canal, fromlist=["channels.%s" % canal])
                        else:
                            channel_verify = __import__('channels.%s' % canal, fromlist=["channels.%s" % canal])
                        logger.debug('Channel %s seems correct' % channel_verify)
                    except:
                        dead_item = Item(multicanal=multicanal,
                                         contentType='movie',
                                         dead=canal,
                                         path=filetools.join(raiz, s),
                                         nfo=nfo_path,
                                         library_urls=new_item.library_urls,
                                         infoLabels={'title': new_item.contentTitle})
                        if canal not in dead_list and canal not in zombie_list:
                            confirm = platformtools.dialog_yesno(config.get_localized_string(30131),
                                                                 config.get_localized_string(30132) % canal.upper(),
                                                                 config.get_localized_string(30133))

                        elif canal in zombie_list:
                            confirm = False
                        else:
                            confirm = True

                        if confirm:
                            delete(dead_item)
                            if canal not in dead_list:
                                dead_list.append(canal)
                            continue
                        else:
                            if canal not in zombie_list:
                                zombie_list.append(canal)

                if len(dead_list) > 0:
                    for canal in dead_list:
                        if canal in new_item.library_urls:
                            del new_item.library_urls[canal]


                new_item.nfo = nfo_path
                new_item.path = filetools.join(raiz, s)
                new_item.thumbnail = new_item.contentThumbnail
                new_item.extra = filetools.join(config.get_setting("videolibrarypath"), config.get_setting("folder_movies"), s)
                strm_path = new_item.strm_path.replace("\\", "/").rstrip("/")
                if '/' in new_item.path:
                    new_item.strm_path = strm_path
                logger.info('EXIST'+ str(local_movie))
                if not filetools.exists(filetools.join(new_item.path, filetools.basename(strm_path))) and local_movie == False:
                    # If strm has been removed from kodi library, don't show it
                    continue

                # Contextual menu: Mark as seen / not seen
                visto = new_item.library_playcounts.get(os.path.splitext(f)[0], 0)
                new_item.infoLabels["playcount"] = visto
                if visto > 0:
                    texto_visto = config.get_localized_string(60016)
                    contador = 0
                else:
                    texto_visto = config.get_localized_string(60017)
                    contador = 1

                # Context menu: Delete series / channel
                num_canales = len(new_item.library_urls)
                if "downloads" in new_item.library_urls:
                    num_canales -= 1
                if num_canales > 1:
                    texto_eliminar = config.get_localized_string(60018)
                else:
                    texto_eliminar = config.get_localized_string(60019)

                new_item.context = [{"title": texto_visto,
                                     "action": "mark_content_as_watched",
                                     "channel": "videolibrary",
                                     "playcount": contador},
                                    {"title": texto_eliminar,
                                     "action": "delete",
                                     "channel": "videolibrary",
                                     "multicanal": multicanal}]
                itemlist.append(new_item)

    if silent == False:
        return sorted(itemlist, key=lambda it: it.title.lower())
    else:
        return


def list_tvshows(item):
    logger.info()
    itemlist = []
    dead_list = []
    zombie_list = []
    lista = []
    # We get all the tvshow.nfo from the SERIES video library recursively
    for raiz, subcarpetas, ficheros in filetools.walk(videolibrarytools.TVSHOWS_PATH):
        for s in subcarpetas:
            tvshow_path = filetools.join(raiz, s, "tvshow.nfo")
            logger.debug(tvshow_path)

            if filetools.exists(tvshow_path):
                # We synchronize the episodes seen from the Kodi video library with that of KoD
                try:
                    # If it's Kodi, we do it
                    if config.is_xbmc():
                        from platformcode import xbmc_videolibrary
                        xbmc_videolibrary.mark_content_as_watched_on_kod(tvshow_path)
                except:
                    logger.error(traceback.format_exc())

                head_nfo, item_tvshow = videolibrarytools.read_nfo(tvshow_path)

                # If you have not read the .nfo well, we will proceed to the next
                if not item_tvshow:
                    logger.error('.nfo erroneous in ' + str(tvshow_path))
                    continue

                if len(item_tvshow.library_urls) > 1:
                    multicanal = True
                else:
                    multicanal = False

                # Verify the existence of the channels. If the channel does not exist, ask yourself if you want to remove the links from that channel.

                for canal in item_tvshow.library_urls:
                    canal = generictools.verify_channel(canal)
                    try:
                        if canal in ['community', 'downloads']:
                            channel_verify = __import__('specials.%s' % canal, fromlist=["channels.%s" % canal])
                        else:
                            channel_verify = __import__('channels.%s' % canal, fromlist=["channels.%s" % canal])
                        logger.debug('Channel %s seems correct' % channel_verify)
                    except:
                        dead_item = Item(multicanal=multicanal,
                                         contentType='tvshow',
                                         dead=canal,
                                         path=filetools.join(raiz, s),
                                         nfo=tvshow_path,
                                         library_urls=item_tvshow.library_urls,
                                         infoLabels={'title': item_tvshow.contentTitle})

                        if canal not in dead_list and canal not in zombie_list:
                            confirm = platformtools.dialog_yesno(config.get_localized_string(30131),
                                                                 config.get_localized_string(30132) % canal.upper(),
                                                                 config.get_localized_string(30133))

                        elif canal in zombie_list:
                            confirm = False
                        else:
                            confirm = True

                        if confirm:
                            delete(dead_item)
                            if canal not in dead_list:
                                dead_list.append(canal)
                            continue
                        else:
                            if canal not in zombie_list:
                                zombie_list.append(canal)

                if len(dead_list) > 0:
                    for canal in dead_list:
                        if canal in item_tvshow.library_urls:
                            del item_tvshow.library_urls[canal]

                # continue loading the elements of the video library

                # Sometimes it gives random errors, for not finding the .nfo. Probably timing issues
                try:
                    item_tvshow.title = item_tvshow.contentTitle
                    item_tvshow.path = filetools.join(raiz, s)
                    item_tvshow.nfo = tvshow_path
                    item_tvshow.extra = filetools.join(config.get_setting("videolibrarypath"), config.get_setting("folder_tvshows"), s)
                    # Contextual menu: Mark as seen / not seen
                    visto = item_tvshow.library_playcounts.get(item_tvshow.contentTitle, 0)
                    item_tvshow.infoLabels["playcount"] = visto
                    if visto > 0:
                        texto_visto = config.get_localized_string(60020)
                        contador = 0
                    else:
                        texto_visto = config.get_localized_string(60021)
                        contador = 1

                except:
                    logger.error('Not find: ' + str(tvshow_path))
                    logger.error(traceback.format_exc())
                    continue

                # Context menu: Automatically search for new episodes or not
                if item_tvshow.active and int(item_tvshow.active) > 0:
                    texto_update = config.get_localized_string(60022)
                    value = 0
                else:
                    texto_update = config.get_localized_string(60023)
                    value = 1
                    item_tvshow.title += " [B]" + u"\u2022".encode('utf-8') + "[/B]"

                # Context menu: Delete series / channel
                num_canales = len(item_tvshow.library_urls)
                if "downloads" in item_tvshow.library_urls:
                    num_canales -= 1
                if num_canales > 1:
                    texto_eliminar = config.get_localized_string(60024)
                else:
                    texto_eliminar = config.get_localized_string(60025)

                item_tvshow.context = [{"title": texto_visto,
                                        "action": "mark_content_as_watched",
                                        "channel": "videolibrary",
                                        "playcount": contador},
                                       {"title": texto_update,
                                        "action": "mark_tvshow_as_updatable",
                                        "channel": "videolibrary",
                                        "active": value},
                                       {"title": texto_eliminar,
                                        "action": "delete",
                                        "channel": "videolibrary",
                                        "multicanal": multicanal},
                                       {"title": config.get_localized_string(70269),
                                        "action": "update_tvshow",
                                        "channel": "videolibrary"}]
                if item_tvshow.local_episodes_path == "":
                    item_tvshow.context.append({"title": config.get_localized_string(80048),
                                                "action": "add_local_episodes",
                                                "channel": "videolibrary"})
                else:
                    item_tvshow.context.append({"title": config.get_localized_string(80049),
                                                "action": "remove_local_episodes",
                                                "channel": "videolibrary"})

                # verify the existence of the channels
                if len(item_tvshow.library_urls) > 0:
                    itemlist.append(item_tvshow)
                    lista.append({'title':item_tvshow.contentTitle,'thumbnail':item_tvshow.thumbnail,'fanart':item_tvshow.fanart, 'active': value, 'nfo':tvshow_path})

    if itemlist:
        itemlist = sorted(itemlist, key=lambda it: it.title.lower())

        itemlist.append(Item(channel=item.channel, action="update_videolibrary", thumbnail=item.thumbnail,
                             title=typo(config.get_localized_string(70269), 'bold color kod'), folder=False))

        itemlist.append(Item(channel=item.channel, action="configure_update_videolibrary", thumbnail=item.thumbnail,
                             title=typo(config.get_localized_string(60599), 'bold color kod'), lista=lista, folder=False))

    return itemlist

def configure_update_videolibrary(item):
    import xbmcgui
    # Load list of options (active user channels that allow global search)
    lista = []
    ids = []
    preselect = []

    for i, item_tvshow in enumerate(item.lista):
        it = xbmcgui.ListItem(item_tvshow["title"], '')
        it.setArt({'thumb': item_tvshow["thumbnail"], 'fanart': item_tvshow["fanart"]})
        lista.append(it)
        ids.append(Item(nfo=item_tvshow['nfo']))
        if item_tvshow['active']<=0:
            preselect.append(i)

    # Select Dialog
    ret = xbmcgui.Dialog().multiselect(config.get_localized_string(60601), lista, preselect=preselect, useDetails=True)
    if ret < 0:
        return False  # order cancel
    seleccionados = [ids[i] for i in ret]

    for tvshow in ids:
        if tvshow not in seleccionados:
            tvshow.active = 0
        elif tvshow in seleccionados:
            tvshow.active = 1
        mark_tvshow_as_updatable(tvshow, silent=True)

    platformtools.itemlist_refresh()

    return True



def get_seasons(item):
    logger.info()
    # logger.debug("item:\n" + item.tostring('\n'))
    itemlist = []
    dict_temp = {}

    videolibrarytools.check_renumber_options(item)

    raiz, carpetas_series, ficheros = next(filetools.walk(item.path))

    # Menu contextual: Releer tvshow.nfo
    head_nfo, item_nfo = videolibrarytools.read_nfo(item.nfo)

    if config.get_setting("no_pile_on_seasons", "videolibrary") == 2:  # Ever
        return get_episodes(item)

    for f in ficheros:
        if f.endswith('.json'):
            season = f.split('x')[0]
            dict_temp[season] = config.get_localized_string(60027) % season

    if config.get_setting("no_pile_on_seasons", "videolibrary") == 1 and len(
            dict_temp) == 1:  # Only if there is a season
        return get_episodes(item)
    else:
        # We create one item for each season
        for season, title in list(dict_temp.items()):
            new_item = item.clone(action="get_episodes", title=title, contentSeason=season,
                                  filtrar_season=True, channel='videolibrary')

            #Contextual menu: Mark the season as viewed or not
            visto = item_nfo.library_playcounts.get("season %s" % season, 0)
            new_item.infoLabels["playcount"] = visto
            if visto > 0:
                texto = config.get_localized_string(60028)
                value = 0
            else:
                texto = config.get_localized_string(60029)
                value = 1
            new_item.context = [{"title": texto,
                                 "action": "mark_season_as_watched",
                                 "channel": "videolibrary",
                                 "playcount": value}]

            # logger.debug("new_item:\n" + new_item.tostring('\n'))
            itemlist.append(new_item)

        if len(itemlist) > 1:
            itemlist = sorted(itemlist, key=lambda it: int(it.contentSeason))

        if config.get_setting("show_all_seasons", "videolibrary"):
            new_item = item.clone(action="get_episodes", title=config.get_localized_string(60030))
            new_item.infoLabels["playcount"] = 0
            itemlist.insert(0, new_item)

        add_download_items(item, itemlist)
    return itemlist


def get_episodes(item):
    logger.info()
    # logger.debug("item:\n" + item.tostring('\n'))
    itemlist = []

    # We get the archives of the episodes
    raiz, carpetas_series, ficheros = next(filetools.walk(item.path))

    # Menu contextual: Releer tvshow.nfo
    head_nfo, item_nfo = videolibrarytools.read_nfo(item.nfo)

    # Create an item in the list for each strm found
    for i in ficheros:
        ext = i.split('.')[-1]
        if ext not in ['json','nfo']:
            season_episode = scrapertools.get_season_and_episode(i)
            if not season_episode:
                # The file does not include the season and episode number
                continue
            season, episode = season_episode.split("x")
            # If there is a filter by season, we ignore the chapters of other seasons
            if item.filtrar_season and int(season) != int(item.contentSeason):
                continue
            # Get the data from the season_episode.nfo
            nfo_path = filetools.join(raiz, '%sx%s.nfo' % (season, episode))
            if filetools.isfile(nfo_path):
                head_nfo, epi = videolibrarytools.read_nfo(nfo_path)

                # Set the chapter title if possible
                if epi.contentTitle:
                    title_episodie = epi.contentTitle.strip()
                else:
                    title_episodie = config.get_localized_string(60031) %  (epi.contentSeason, str(epi.contentEpisodeNumber).zfill(2))

                epi.contentTitle = "%sx%s" % (epi.contentSeason, str(epi.contentEpisodeNumber).zfill(2))
                epi.title = "%sx%s - %s" % (epi.contentSeason, str(epi.contentEpisodeNumber).zfill(2), title_episodie)

                if item_nfo.library_filter_show:
                    epi.library_filter_show = item_nfo.library_filter_show

                # Contextual menu: Mark episode as seen or not
                visto = item_nfo.library_playcounts.get(season_episode, 0)
                epi.infoLabels["playcount"] = visto
                if visto > 0:
                    texto = config.get_localized_string(60032)
                    value = 0
                else:
                    texto = config.get_localized_string(60033)
                    value = 1
                epi.context = [{"title": texto,
                                "action": "mark_content_as_watched",
                                "channel": "videolibrary",
                                "playcount": value,
                                "nfo": item.nfo}]
                if ext != 'strm':
                    epi.local = True
                itemlist.append(epi)

    itemlist = sorted(itemlist, key=lambda it: (int(it.contentSeason), int(it.contentEpisodeNumber)))
    add_download_items(item, itemlist)
    return itemlist


def findvideos(item):
    from specials import autoplay
    logger.info()
    # logger.debug("item:\n" + item.tostring('\n'))
    videolibrarytools.check_renumber_options(item)
    itemlist = []
    list_canales = {}
    item_local = None

    # Disable autoplay
    # autoplay.set_status(False)

    if not item.contentTitle or not item.strm_path:
        logger.debug("Unable to search for videos due to lack of parameters")
        return []

    content_title = str(item.contentSeason) + 'x' + (str(item.contentEpisodeNumber) if item.contentEpisodeNumber > 9 else '0' + str(item.contentEpisodeNumber))
    if item.contentType == 'movie':
        item.strm_path = filetools.join(videolibrarytools.MOVIES_PATH, item.strm_path)
        path_dir = filetools.dirname(item.strm_path)
        item.nfo = filetools.join(path_dir, filetools.basename(path_dir) + ".nfo")
    else:
        item.strm_path = filetools.join(videolibrarytools.TVSHOWS_PATH, item.strm_path)
        path_dir = filetools.dirname(item.strm_path)
        item.nfo = filetools.join(path_dir, 'tvshow.nfo')

    for fd in filetools.listdir(path_dir):
        if fd.endswith('.json'):
            contenido, nom_canal = fd[:-6].split('[')
            if (contenido.startswith(content_title) or item.contentType == 'movie') and nom_canal not in list(list_canales.keys()):
                list_canales[nom_canal] = filetools.join(path_dir, fd)

    num_canales = len(list_canales)

    if 'downloads' in list_canales:
        json_path = list_canales['downloads']
        item_json = Item().fromjson(filetools.read(json_path))
        item_json.contentChannel = "local"
        # Support for relative paths in downloads
        if filetools.is_relative(item_json.url):
            item_json.url = filetools.join(videolibrarytools.VIDEOLIBRARY_PATH, item_json.url)

        del list_canales['downloads']

        # Check that the video has not been deleted
        if filetools.exists(item_json.url):
            item_local = item_json.clone(action='play')
            itemlist.append(item_local)
        else:
            num_canales -= 1

    filtro_canal = ''
    if num_canales > 1 and config.get_setting("ask_channel", "videolibrary"):
        opciones = [config.get_localized_string(70089) % k.capitalize() for k in list(list_canales.keys())]
        opciones.insert(0, config.get_localized_string(70083))
        if item_local:
            opciones.append(item_local.title)

        from platformcode import platformtools
        index = platformtools.dialog_select(config.get_localized_string(30163), opciones)
        if index < 0:
            return []

        elif item_local and index == len(opciones) - 1:
            filtro_canal = 'downloads'
            platformtools.play_video(item_local)

        elif index > 0:
            filtro_canal = opciones[index].replace(config.get_localized_string(70078), "").strip()
            itemlist = []

    for nom_canal, json_path in list(list_canales.items()):
        if filtro_canal and filtro_canal != nom_canal.capitalize():
            continue

        item_canal = Item()

        # We import the channel of the selected part
        try:
            if nom_canal == 'community':
                channel = __import__('specials.%s' % nom_canal, fromlist=["channels.%s" % nom_canal])
            else:
                channel = __import__('channels.%s' % nom_canal, fromlist=["channels.%s" % nom_canal])
        except ImportError:
            exec("import channels." + nom_canal + " as channel")

        item_json = Item().fromjson(filetools.read(json_path))
        list_servers = []

        try:
            # FILTERTOOLS
            # if the channel has a filter, the name it has saved is passed to it so that it filters correctly.
            if "list_language" in item_json:
                # if it comes from the addon video library
                if "library_filter_show" in item:
                    item_json.show = item.library_filter_show.get(nom_canal, "")

            # We run find_videos, from the channel or common
            item_json.contentChannel = 'videolibrary'
            if hasattr(channel, 'findvideos'):
                from core import servertools
                if item_json.videolibray_emergency_urls:
                    del item_json.videolibray_emergency_urls
                list_servers = getattr(channel, 'findvideos')(item_json)
                list_servers = servertools.filter_servers(list_servers)
            elif item_json.action == 'play':
                from platformcode import platformtools
                # autoplay.set_status(True)
                item_json.contentChannel = item_json.channel
                item_json.channel = "videolibrary"
                platformtools.play_video(item_json)
                return ''
            else:
                from core import servertools
                list_servers = servertools.find_video_items(item_json)
        except Exception as ex:
            logger.error("The findvideos function for the channel %s failed" % nom_canal)
            template = "An exception of type %s occured. Arguments:\n%r"
            message = template % (type(ex).__name__, ex.args)
            logger.error(message)
            logger.error(traceback.format_exc())

        # Change the title to the servers adding the name of the channel in front and the infoLabels and the images of the item if the server does not have
        for server in list_servers:
            server.contentChannel = server.channel
            server.channel = "videolibrary"
            server.nfo = item.nfo
            server.strm_path = item.strm_path
            server.play_from = item.play_from

            # Kodi 18 Compatibility - Prevents wheel from spinning around in Direct Links
            if server.action == 'play':
                server.folder = False

            # Channel name is added if desired
            if config.get_setting("quit_channel_name", "videolibrary") == 0:
                server.title = "%s: %s" % (nom_canal.capitalize(), server.title)

            if not server.thumbnail:
                server.thumbnail = item.thumbnail

            # logger.debug("server:\n%s" % server.tostring('\n'))
            itemlist.append(server)

    if autoplay.play_multi_channel(item, itemlist):  # hideserver
        return []
    from inspect import stack
    from specials import nextep
    if nextep.check(item) and stack()[1][3] == 'run':
        nextep.videolibrary(item)
    add_download_items(item, itemlist)
    return itemlist


def play(item):
    logger.info()
    # logger.debug("item:\n" + item.tostring('\n'))

    if not item.contentChannel == "local":
        if item.contentChannel == 'community':
            channel = __import__('specials.%s' % item.contentChannel, fromlist=["channels.%s" % item.contentChannel])
        else:
            channel = __import__('channels.%s' % item.contentChannel, fromlist=["channels.%s" % item.contentChannel])
        if hasattr(channel, "play"):
            itemlist = getattr(channel, "play")(item)

        else:
            itemlist = [item.clone()]
    else:
        itemlist = [item.clone(url=item.url, server="local")]

    # For direct links in list format
    if isinstance(itemlist[0], list):
        item.video_urls = itemlist
        itemlist = [item]

    # This is necessary in case the channel play deletes the data
    for v in itemlist:
        if isinstance(v, Item):
            v.nfo = item.nfo
            v.strm_path = item.strm_path
            v.infoLabels = item.infoLabels
            if item.contentTitle:
                v.title = item.contentTitle
            else:
                if item.contentType == "episode":
                    v.title = config.get_localized_string(60036) % item.contentEpisodeNumber
            v.thumbnail = item.thumbnail
            v.contentThumbnail = item.thumbnail
            v.contentChannel = item.contentChannel

    return itemlist


def update_videolibrary(item=''):
    logger.info()

    # Update active series by overwriting
    import service
    service.check_for_update(overwrite=True)

    # Delete movie folders that do not contain strm file
    for raiz, subcarpetas, ficheros in filetools.walk(videolibrarytools.MOVIES_PATH):
        strm = False
        for f in ficheros:
            if f.endswith(".strm"):
                strm = True
                break

        if ficheros and not strm:
            logger.debug("Deleting deleted movie folder: %s" % raiz)
            filetools.rmdirtree(raiz)


def move_videolibrary(current_path, new_path, current_movies_folder, new_movies_folder, current_tvshows_folder, new_tvshows_folder):
    logger.info()

    backup_current_path = current_path
    backup_new_path = new_path

    logger.info('current_path: ' + current_path)
    logger.info('new_path: ' + new_path)
    logger.info('current_movies_folder: ' + current_movies_folder)
    logger.info('new_movies_folder: ' + new_movies_folder)
    logger.info('current_tvshows_folder: ' + current_tvshows_folder)
    logger.info('new_tvshows_folder: ' + new_tvshows_folder)

    notify = False
    progress = platformtools.dialog_progress_bg(config.get_localized_string(20000), config.get_localized_string(80011))
    current_path = xbmc.translatePath(current_path)
    new_path = xbmc.translatePath(new_path)
    current_movies_path = filetools.join(current_path, current_movies_folder)
    new_movies_path = filetools.join(new_path, new_movies_folder)
    current_tvshows_path = os.path.join(current_path, current_tvshows_folder)
    new_tvshows_path = os.path.join(new_path, new_tvshows_folder)

    logger.info('current_movies_path: ' + current_movies_path)
    logger.info('new_movies_path: ' + new_movies_path)
    logger.info('current_tvshows_path: ' + current_tvshows_path)
    logger.info('new_tvshows_path: ' + new_tvshows_path)

    from platformcode import xbmc_videolibrary
    movies_path, tvshows_path = xbmc_videolibrary.check_sources(new_movies_path, new_tvshows_path)
    logger.info('check_sources: ' + str(movies_path) + ', ' + str(tvshows_path))
    if movies_path or tvshows_path:
        if not movies_path:
            filetools.rmdir(new_movies_path)
        if not tvshows_path:
            filetools.rmdir(new_tvshows_path)
        config.set_setting("videolibrarypath", backup_current_path)
        config.set_setting("folder_movies", current_movies_folder)
        config.set_setting("folder_tvshows", current_tvshows_folder)
        xbmc_videolibrary.update_sources(backup_current_path, backup_new_path)
        progress.update(100)
        xbmc.sleep(1000)
        progress.close()
        platformtools.dialog_ok(config.get_localized_string(20000), config.get_localized_string(80028))
        return

    config.verify_directories_created()
    progress.update(10, config.get_localized_string(20000), config.get_localized_string(80012))
    if current_movies_path != new_movies_path:
        if filetools.listdir(current_movies_path):
            dir_util.copy_tree(current_movies_path, new_movies_path)
            notify = True
        filetools.rmdirtree(current_movies_path)
    progress.update(40)
    if current_tvshows_path != new_tvshows_path:
        if filetools.listdir(current_tvshows_path):
            dir_util.copy_tree(current_tvshows_path, new_tvshows_path)
            notify = True
        filetools.rmdirtree(current_tvshows_path)
    progress.update(70)
    if current_path != new_path and not filetools.listdir(current_path) and not "plugin.video.kod\\videolibrary" in current_path:
        filetools.rmdirtree(current_path)

    xbmc_videolibrary.update_sources(backup_new_path, backup_current_path)
    if config.is_xbmc() and config.get_setting("videolibrary_kodi"):
        xbmc_videolibrary.update_db(backup_current_path, backup_new_path, current_movies_folder, new_movies_folder, current_tvshows_folder, new_tvshows_folder, progress)
    else:
        progress.update(100)
        xbmc.sleep(1000)
        progress.close()
    if notify:
        platformtools.dialog_notification(config.get_localized_string(20000), config.get_localized_string(80014), time=5000, sound=False)


def delete_videolibrary(item):
    logger.info()

    if not platformtools.dialog_yesno(config.get_localized_string(20000), config.get_localized_string(80037)):
        return

    p_dialog = platformtools.dialog_progress_bg(config.get_localized_string(20000), config.get_localized_string(80038))
    p_dialog.update(0)

    if config.is_xbmc() and config.get_setting("videolibrary_kodi"):
        from platformcode import xbmc_videolibrary
        xbmc_videolibrary.clean()
    p_dialog.update(10)
    filetools.rmdirtree(videolibrarytools.MOVIES_PATH)
    p_dialog.update(50)
    filetools.rmdirtree(videolibrarytools.TVSHOWS_PATH)
    p_dialog.update(90)

    config.verify_directories_created()
    p_dialog.update(100)
    xbmc.sleep(1000)
    p_dialog.close()
    platformtools.dialog_notification(config.get_localized_string(20000), config.get_localized_string(80039), time=5000, sound=False)


# context menu methods
def update_tvshow(item):
    logger.info()
    # logger.debug("item:\n" + item.tostring('\n'))

    heading = config.get_localized_string(60037)
    p_dialog = platformtools.dialog_progress_bg(config.get_localized_string(20000), heading)
    p_dialog.update(0, heading, item.contentSerieName)

    import service
    if service.update(item.path, p_dialog, 0, 100, item, False) and config.is_xbmc() and config.get_setting("videolibrary_kodi"):
        from platformcode import xbmc_videolibrary
        xbmc_videolibrary.update(folder=filetools.basename(item.path))

    p_dialog.close()

    # check if the TV show is ended or has been canceled and ask the user to remove it from the video library update
    nfo_path = filetools.join(item.path, "tvshow.nfo")
    head_nfo, item_nfo = videolibrarytools.read_nfo(nfo_path)
    if item.active and not item_nfo.active:
        if not platformtools.dialog_yesno(config.get_localized_string(60037).replace('...',''), config.get_localized_string(70268) % item.contentSerieName):
            item_nfo.active = 1
            filetools.write(nfo_path, head_nfo + item_nfo.tojson())

    platformtools.itemlist_refresh()


def add_local_episodes(item):
    logger.info()

    done, local_episodes_path = videolibrarytools.config_local_episodes_path(item.path, item.contentSerieName, silent=True)
    if done < 0:
        logger.info("An issue has occurred while configuring local episodes")
    elif local_episodes_path:
        nfo_path = filetools.join(item.path, "tvshow.nfo")
        head_nfo, item_nfo = videolibrarytools.read_nfo(nfo_path)
        item_nfo.local_episodes_path = local_episodes_path
        if not item_nfo.active:
            item_nfo.active = 1
        filetools.write(nfo_path, head_nfo + item_nfo.tojson())

        update_tvshow(item)

        platformtools.itemlist_refresh()


def remove_local_episodes(item):
    logger.info()

    nfo_path = filetools.join(item.path, "tvshow.nfo")
    head_nfo, item_nfo = videolibrarytools.read_nfo(nfo_path)

    for season_episode in item_nfo.local_episodes_list:
        filetools.remove(filetools.join(item.path, season_episode + '.strm'))

    item_nfo.local_episodes_list = []
    item_nfo.local_episodes_path = ''
    filetools.write(nfo_path, head_nfo + item_nfo.tojson())

    update_tvshow(item)

    platformtools.itemlist_refresh()


def verify_playcount_series(item, path):
    logger.info()

    """
    This method reviews and repairs the PlayCount of a series that has become out of sync with the actual list of episodes in its folder. Entries for missing episodes, seasons, or series are created with the "not seen" mark. Later it is sent to verify the counters of Seasons and Series
    On return it sends status of True if updated or False if not, usually by mistake. With this status, the caller can update the status of the "verify_playcount" option in "videolibrary.py". The intention of this method is to give a pass that repairs all the errors and then deactivate it. It can be reactivated in the Alpha Video Library menu.

    """
    #logger.debug("item:\n" + item.tostring('\n'))

    # If you have never done verification, we force it
    estado = config.get_setting("verify_playcount", "videolibrary")
    if not estado or estado == False:
        estado = True                                                               # If you have never done verification, we force it
    else:
        estado = False

    if item.contentType == 'movie':                                                 # This is only for Series
        return (item, False)
    if filetools.exists(path):
        nfo_path = filetools.join(path, "tvshow.nfo")
        head_nfo, it = videolibrarytools.read_nfo(nfo_path)                         # We get the .nfo of the Series
        if not hasattr(it, 'library_playcounts') or not it.library_playcounts:      # If the .nfo does not have library_playcounts we will create it for you
            logger.error('** It does not have PlayCount')
            it.library_playcounts = {}

        # We get the archives of the episodes
        raiz, carpetas_series, ficheros = next(filetools.walk(path))
        # Create an item in the list for each strm found
        estado_update = False
        for i in ficheros:
            if i.endswith('.strm'):
                season_episode = scrapertools.get_season_and_episode(i)
                if not season_episode:
                    # The file does not include the season and episode number
                    continue
                season, episode = season_episode.split("x")
                if season_episode not in it.library_playcounts:                     # The episode is not included
                    it.library_playcounts.update({season_episode: 0})               # update the .nfo playCount
                    estado_update = True                                            # We mark that we have updated something

                if 'season %s' % season not in it.library_playcounts:               # Season is not included
                    it.library_playcounts.update({'season %s' % season: 0})         # update the .nfo playCount
                    estado_update = True                                            # We mark that we have updated something

                if it.contentSerieName not in it.library_playcounts:                # Series not included
                    it.library_playcounts.update({item.contentSerieName: 0})        # update the .nfo playCount
                    estado_update = True                                            # We mark that we have updated something

        if estado_update:
            logger.error('** Update status: ' + str(estado) + ' / PlayCount: ' + str(it.library_playcounts))
            estado = estado_update
        # it is verified that if all the episodes of a season are marked, tb the season is marked
        for key, value in it.library_playcounts.items():
            if key.startswith("season"):
                season = scrapertools.find_single_match(key, r'season (\d+)')        # We obtain in no. seasonal
                it = check_season_playcount(it, season)
        # We save the changes to item.nfo
        if filetools.write(nfo_path, head_nfo + it.tojson()):
            return (it, estado)
    return (item, False)


def mark_content_as_watched2(item):
    logger.info()
    # logger.debug("item:\n" + item.tostring('\n'))
    if filetools.isfile(item.nfo):
        head_nfo, it = videolibrarytools.read_nfo(item.nfo)
        name_file = ""
        if item.contentType == 'movie' or item.contentType == 'tvshow':
            name_file = os.path.splitext(filetools.basename(item.nfo))[0]

            if name_file != 'tvshow' :
                it.library_playcounts.update({name_file: item.playcount})

        if item.contentType == 'episode' or item.contentType == 'tvshow' or item.contentType == 'list' or name_file == 'tvshow':
            name_file = os.path.splitext(filetools.basename(item.strm_path))[0]
            num_season = name_file [0]
            item.__setattr__('contentType', 'episode')
            item.__setattr__('contentSeason', num_season)

        else:
            name_file = item.contentTitle

        if not hasattr(it, 'library_playcounts'):
            it.library_playcounts = {}
        it.library_playcounts.update({name_file: item.playcount})

        # it is verified that if all the episodes of a season are marked, tb the season is marked
        if item.contentType != 'movie':
            it = check_season_playcount(it, item.contentSeason)

        # We save the changes to item.nfo
        if filetools.write(item.nfo, head_nfo + it.tojson()):
            item.infoLabels['playcount'] = item.playcount

            if config.is_xbmc():
                from platformcode import xbmc_videolibrary
                xbmc_videolibrary.mark_content_as_watched_on_kodi(item , item.playcount)


def mark_content_as_watched(item):
    logger.info()
    #logger.debug("item:\n" + item.tostring('\n'))

    if filetools.exists(item.nfo):
        head_nfo, it = videolibrarytools.read_nfo(item.nfo)

        if item.contentType == 'movie':
            name_file = os.path.splitext(filetools.basename(item.nfo))[0]
        elif item.contentType == 'episode':
            name_file = "%sx%s" % (item.contentSeason, str(item.contentEpisodeNumber).zfill(2))
        else:
            name_file = item.contentTitle

        if not hasattr(it, 'library_playcounts'):
            it.library_playcounts = {}
        it.library_playcounts.update({name_file: item.playcount})

        # it is verified that if all the episodes of a season are marked, tb the season is marked
        if item.contentType != 'movie':
            it = check_season_playcount(it, item.contentSeason)

        # We save the changes to item.nfo
        if filetools.write(item.nfo, head_nfo + it.tojson()):
            item.infoLabels['playcount'] = item.playcount

            if item.contentType == 'tvshow' and item.type != 'episode' :
                # Update entire series
                new_item = item.clone(contentSeason=-1)
                mark_season_as_watched(new_item)

            if config.is_xbmc():
                from platformcode import xbmc_videolibrary
                xbmc_videolibrary.mark_content_as_watched_on_kodi(item, item.playcount)

            platformtools.itemlist_refresh()


def mark_season_as_watched(item):
    logger.info()
    # logger.debug("item:\n" + item.tostring('\n'))

    # Get dictionary of marked episodes
    f = filetools.join(item.path, 'tvshow.nfo')
    head_nfo, it = videolibrarytools.read_nfo(f)
    if not hasattr(it, 'library_playcounts'):
        it.library_playcounts = {}

    # We get the archives of the episodes
    raiz, carpetas_series, ficheros = next(filetools.walk(item.path))

    # We mark each of the episodes found this season
    episodios_marcados = 0
    for i in ficheros:
        if i.endswith(".strm"):
            season_episode = scrapertools.get_season_and_episode(i)
            if not season_episode:
                # The file does not include the season and episode number
                continue
            season, episode = season_episode.split("x")

            if int(item.contentSeason) == -1 or int(season) == int(item.contentSeason):
                name_file = os.path.splitext(filetools.basename(i))[0]
                it.library_playcounts[name_file] = item.playcount
                episodios_marcados += 1

    if episodios_marcados:
        if int(item.contentSeason) == -1:
            # We add all seasons to the dictionary item.library_playcounts
            for k in list(it.library_playcounts.keys()):
                if k.startswith("season"):
                    it.library_playcounts[k] = item.playcount
        else:
            # Add season to dictionary item.library_playcounts
            it.library_playcounts["season %s" % item.contentSeason] = item.playcount

            # it is verified that if all the seasons are seen, the series is marked as view
            it = check_tvshow_playcount(it, item.contentSeason)

        # We save the changes to tvshow.nfo
        filetools.write(f, head_nfo + it.tojson())
        item.infoLabels['playcount'] = item.playcount

        if config.is_xbmc():
            # We update the Kodi database
            from platformcode import xbmc_videolibrary
            xbmc_videolibrary.mark_season_as_watched_on_kodi(item, item.playcount)

    platformtools.itemlist_refresh()


def mark_tvshow_as_updatable(item, silent=False):
    logger.info()
    head_nfo, it = videolibrarytools.read_nfo(item.nfo)
    it.active = item.active
    filetools.write(item.nfo, head_nfo + it.tojson())

    if not silent:
        platformtools.itemlist_refresh()


def delete(item):
    def delete_all(_item):
        for file in filetools.listdir(_item.path):
            if file.endswith(".strm") or file.endswith(".nfo") or file.endswith(".json")or file.endswith(".torrent"):
                filetools.remove(filetools.join(_item.path, file))

        if _item.contentType == 'movie':
            heading = config.get_localized_string(70084)
        else:
            heading = config.get_localized_string(70085)

        if config.is_xbmc() and config.get_setting("videolibrary_kodi"):
            from platformcode import xbmc_videolibrary
            if _item.local_episodes_path:
                platformtools.dialog_ok(heading, config.get_localized_string(80047) % _item.infoLabels['title'])
            path_list = [_item.extra]
            xbmc_videolibrary.clean(path_list)

        raiz, carpeta_serie, ficheros = next(filetools.walk(_item.path))
        if ficheros == []:
            filetools.rmdir(_item.path)
        elif platformtools.dialog_yesno(heading, config.get_localized_string(70081) % os.path.basename(_item.path)):
            filetools.rmdirtree(_item.path)

        logger.info("All links removed")
        xbmc.sleep(1000)
        platformtools.itemlist_refresh()

    # logger.debug(item.tostring('\n'))

    if item.contentType == 'movie':
        heading = config.get_localized_string(70084)
    else:
        heading = config.get_localized_string(70085)
    if item.multicanal:
        # Get channel list
        if item.dead == '':
            opciones = []
            channels = []
            for k in list(item.library_urls.keys()):
                if k != "downloads":
                    opciones.append(config.get_localized_string(70086) % k.capitalize())
                    channels.append(k)
            opciones.insert(0, heading)

            index = platformtools.dialog_select(config.get_localized_string(30163), opciones)

            if index == 0:
                # Selected Delete movie / series
                delete_all(item)
                return

            elif index > 0:
                # Selected Delete channel X
                canal = opciones[index].replace(config.get_localized_string(70079), "").lower()
                channels.remove(canal)
            else:
                return
        else:
            canal = item.dead

        num_enlaces = 0
        path_list = []
        for fd in filetools.listdir(item.path):
            if fd.endswith(canal + '].json') or scrapertools.find_single_match(fd, r'%s]_\d+.torrent' % canal):
                if filetools.remove(filetools.join(item.path, fd)):
                    num_enlaces += 1
                    # Remove strm and nfo if no other channel
                    episode = fd.replace(' [' + canal + '].json', '')
                    found_ch = False
                    for ch in channels:
                        if filetools.exists(filetools.join(item.path, episode + ' [' + ch + '].json')):
                            found_ch = True
                            break
                    if found_ch == False:
                        filetools.remove(filetools.join(item.path, episode + '.nfo'))
                        strm_path = filetools.join(item.path, episode + '.strm')
                        # if it is a local episode, do not delete the strm
                        if 'plugin://plugin.video.kod/?' in filetools.read(strm_path):
                            filetools.remove(strm_path)
                            path_list.append(filetools.join(item.extra, episode + '.strm'))

        if config.is_xbmc() and config.get_setting("videolibrary_kodi") and path_list:
            from platformcode import xbmc_videolibrary
            xbmc_videolibrary.clean(path_list)

        if num_enlaces > 0:
            # Update .nfo
            head_nfo, item_nfo = videolibrarytools.read_nfo(item.nfo)
            del item_nfo.library_urls[canal]
            if item_nfo.emergency_urls and item_nfo.emergency_urls.get(canal, False):
                del item_nfo.emergency_urls[canal]
            filetools.write(item.nfo, head_nfo + item_nfo.tojson())

        msg_txt = config.get_localized_string(70087) % (num_enlaces, canal)
        logger.info(msg_txt)
        platformtools.dialog_notification(heading, msg_txt)
        platformtools.itemlist_refresh()

    else:
        if platformtools.dialog_yesno(heading, config.get_localized_string(70088) % item.infoLabels['title']):
            delete_all(item)


def check_season_playcount(item, season):
    logger.info()

    if season:
        episodios_temporada = 0
        episodios_vistos_temporada = 0
        for key, value in item.library_playcounts.items():
            if key.startswith("%sx" % season):
                episodios_temporada += 1
                if value > 0:
                    episodios_vistos_temporada += 1

        if episodios_temporada == episodios_vistos_temporada:
            # it is verified that if all the seasons are seen, the series is marked as view
            item.library_playcounts.update({"season %s" % season: 1})
        else:
            # it is verified that if all the seasons are seen, the series is marked as view
            item.library_playcounts.update({"season %s" % season: 0})

    return check_tvshow_playcount(item, season)


def check_tvshow_playcount(item, season):
    logger.info()
    if season:
        temporadas_serie = 0
        temporadas_vistas_serie = 0
        for key, value in item.library_playcounts.items():
            if key.startswith("season" ):
                temporadas_serie += 1
                if value > 0:
                    temporadas_vistas_serie += 1

        if temporadas_serie == temporadas_vistas_serie:
            item.library_playcounts.update({item.title: 1})
        else:
            item.library_playcounts.update({item.title: 0})

    else:
        playcount = item.library_playcounts.get(item.title, 0)
        item.library_playcounts.update({item.title: playcount})

    return item


def add_download_items(item, itemlist):
    if config.get_setting('downloadenabled'):
        localOnly = True
        for i in itemlist:
            if i.contentChannel != 'local':
                localOnly = False
                break
        if not item.fromLibrary and not localOnly:
            downloadItem = Item(channel='downloads',
                                from_channel=item.channel,
                                title=typo(config.get_localized_string(60355), "color kod bold"),
                                fulltitle=item.fulltitle,
                                show=item.fulltitle,
                                contentType=item.contentType,
                                contentSerieName=item.contentSerieName,
                                url=item.url,
                                action='save_download',
                                from_action="findvideos",
                                contentTitle=item.contentTitle,
                                path=item.path,
                                thumbnail=thumb(thumb='downloads.png'),
                                parent=item.tourl())
            if item.action == 'findvideos':
                if item.contentType == 'episode':
                    downloadItem.title = typo(config.get_localized_string(60356), "color kod bold")
                else:  # film
                    downloadItem.title = typo(config.get_localized_string(60354), "color kod bold")
                downloadItem.downloadItemlist = [i.tourl() for i in itemlist]
                itemlist.append(downloadItem)
            else:
                if item.contentSeason:  # season
                    downloadItem.title = typo(config.get_localized_string(60357), "color kod bold")
                    itemlist.append(downloadItem)
                else:  # tvshow + not seen
                    itemlist.append(downloadItem)
                    itemlist.append(downloadItem.clone(title=typo(config.get_localized_string(60003), "color kod bold"), unseen=True))