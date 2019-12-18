# -*- coding: utf-8 -*-
# -*- Channel New Search -*-
# -*- Created for Alfa-addon -*-
# -*- By the Alfa Develop Group -*-

import os
import json
import time
from lib.concurrent import futures
from core.item import Item
from core import tmdb
from core import scrapertools
from core import channeltools
import channelselector
from channelselector import get_thumb
from platformcode import logger
from platformcode import config
from platformcode import platformtools
from platformcode import unify
from core.support import typo

import xbmcaddon
addon = xbmcaddon.Addon('metadata.themoviedb.org')
def_lang = addon.getSetting('language')

def mainlist(item):
    logger.info()

    itemlist = list()

    itemlist.append(Item(channel=item.channel, title=config.get_localized_string(30103), action='new_search', mode='all',
                         thumbnail=get_thumb("search.png")))

    itemlist.append(Item(channel=item.channel, title=config.get_localized_string(70741) % config.get_localized_string(30122), action='new_search', mode='movie',
                         thumbnail=get_thumb("search_movie.png")))

    itemlist.append(Item(channel=item.channel, title=config.get_localized_string(70741) % config.get_localized_string(30123), action='new_search', mode='tvshow',
                         thumbnail=get_thumb("search_tvshow.png")))

    itemlist.append(Item(channel=item.channel, title=config.get_localized_string(70741) % config.get_localized_string(70314), action='new_search',
                         page=1, mode='person', thumbnail=get_thumb("search_star.png")))

    itemlist.append(Item(channel=item.channel, title=config.get_localized_string(60420), action='sub_menu',
                         thumbnail=get_thumb('search.png')))

    itemlist.append(Item(channel=item.channel, title=config.get_localized_string(59994), action='opciones',
                         thumbnail=get_thumb('setting_0.png')))

    itemlist = set_context(itemlist)

    return itemlist


def sub_menu(item):
    logger.info()

    itemlist = list()

    itemlist.append(Item(channel=item.channel, action='genres_menu', title=config.get_localized_string(70306),
                         mode='movie', thumbnail=get_thumb("channels_movie_genre.png")))

    itemlist.append(Item(channel=item.channel, action='years_menu', title=config.get_localized_string(70742),
                         mode='movie', thumbnail=get_thumb("channels_movie_year.png")))

    itemlist.append(Item(channel=item.channel, action='discover_list', title=config.get_localized_string(70307),
                         search_type='list', list_type='movie/popular', mode='movie',
                         thumbnail=get_thumb("channels_movie_popular.png")))

    itemlist.append(Item(channel=item.channel, action='discover_list', title=config.get_localized_string(70308),
                         search_type='list', list_type='movie/top_rated', mode='movie',
                         thumbnail=get_thumb("channels_movie_top.png")))

    itemlist.append(Item(channel=item.channel, action='discover_list', title=config.get_localized_string(70309),
                         search_type='list', list_type='movie/now_playing', mode='movie',
                         thumbnail=get_thumb("channels_movie_now_playing.png")))

    itemlist.append(Item(channel=item.channel, action='genres_menu', title=config.get_localized_string(70310),
                         mode='tvshow', thumbnail=get_thumb("channels_tvshow_genre.png")))

    itemlist.append(Item(channel=item.channel, action='years_menu', title=config.get_localized_string(70743),
                         mode='tvshow', thumbnail=get_thumb("channels_tvshow_year.png")))

    itemlist.append(Item(channel=item.channel, action='discover_list', title=config.get_localized_string(70311),
                         search_type='list', list_type='tv/popular', mode='tvshow',
                         thumbnail=get_thumb("popular.png")))

    itemlist.append(Item(channel=item.channel, action='discover_list', title=config.get_localized_string(70312),
                         search_type='list', list_type='tv/on_the_air', mode='tvshow',
                         thumbnail=get_thumb("channels_tvshow_on_the_air.png")))

    itemlist.append(Item(channel=item.channel, action='discover_list', title=config.get_localized_string(70313),
                         search_type='list', list_type='tv/top_rated', mode='tvshow',
                         thumbnail=get_thumb("channels_tvshow_top.png")))

    itemlist.append(Item(channel="tvmoviedb", action="mainlist", title=config.get_localized_string(70274),
                         thumbnail=get_thumb("search.png")))

    itemlist = set_context(itemlist)

    return itemlist


def new_search(item):
    logger.info()

    itemlist = []

    last_search = channeltools.get_channel_setting('Last_searched', 'search', '')
    searched_text = platformtools.dialog_input(default=last_search, heading='')

    if not searched_text:
        return

    channeltools.set_channel_setting('Last_searched', searched_text, 'search')
    searched_text = searched_text.replace("+", " ")

    if item.mode == 'person':
        item.searched_text = searched_text
        return actor_list(item)

    if item.mode != 'all':
        tmdb_info = tmdb.Tmdb(texto_buscado=searched_text, tipo=item.mode.replace('show', ''))
        results = tmdb_info.results
        for result in results:
            result = tmdb_info.get_infoLabels(result, origen=result)
            if item.mode == 'movie':
                title = result['title']
            else:
                title = result['name']
                item.mode = 'tvshow'

            thumbnail = result.get('thumbnail', '')
            fanart = result.get('fanart', '')

            new_item = Item(channel=item.channel,
                            action='channel_search',
                            title=title,
                            text=searched_text,
                            thumbnail=thumbnail,
                            fanart=fanart,
                            mode=item.mode,
                            infoLabels=result)

            if item.mode == 'movie':
                new_item.contentTitle = result['title']
            else:
                new_item.contentSerieName = result['name']

            itemlist.append(new_item)

    if item.mode == 'all' or not itemlist:
        itemlist = channel_search(Item(channel=item.channel,
                                       title=searched_text,
                                       text=searched_text,
                                       mode='all',
                                       infoLabels={}))

    return itemlist


def channel_search(item):
    logger.info()

    start = time.time()
    searching = list()
    results = list()
    valid = list()
    ch_list = dict()
    to_temp = dict()
    mode = item.mode
    max_results = 10

    searched_id = item.infoLabels['tmdb_id']

    channel_list = get_channels(item)

    from lib import cloudscraper
    session = cloudscraper.create_scraper()

    searching += channel_list
    cnt = 0

    progress = platformtools.dialog_progress(config.get_localized_string(30993) % item.title, config.get_localized_string(70744) % len(channel_list),
                                             str(searching))
    config.set_setting('tmdb_active', False)

    with futures.ThreadPoolExecutor() as executor:
        c_results = [executor.submit(get_channel_results, ch, item, session) for ch in channel_list]

        for res in futures.as_completed(c_results):
            cnt += 1
            finished = res.result()[0]
            if res.result()[1]:
                ch_list[res.result()[0]] = res.result()[1]

            if progress.iscanceled():
                break
            if finished in searching:
                searching.remove(finished)
                progress.update((cnt * 100) / len(channel_list), config.get_localized_string(70744) % str(len(channel_list) - cnt),
                                str(searching))

    progress.close()

    cnt = 0
    progress = platformtools.dialog_progress(config.get_localized_string(30993) % item.title, config.get_localized_string(60295),
                                             config.get_localized_string(60293))

    config.set_setting('tmdb_active', True)
    res_count = 0
    for key, value in ch_list.items():
        grouped = list()
        cnt += 1
        progress.update((cnt * 100) / len(ch_list), config.get_localized_string(60295), config.get_localized_string(60293))
        if len(value) <= max_results and item.mode != 'all':
            if len(value) == 1:
                if not value[0].action or config.get_localized_string(70006).lower() in value[0].title.lower():
                    continue
            tmdb.set_infoLabels_itemlist(value, True, forced=True)
            for elem in value:
                if not elem.infoLabels.get('year', ""):
                    elem.infoLabels['year'] = '-'
                    tmdb.set_infoLabels_item(elem, True)

                if elem.infoLabels['tmdb_id'] == searched_id:
                    elem.from_channel = key
                    if not config.get_setting('unify'):
                        elem.title += ' [%s]' % key
                    valid.append(elem)

        for it in value:
            if it.channel == item.channel:
                it.channel = key
            if it in valid:
                continue
            if mode == 'all' or (it.contentType and mode == it.contentType):
                grouped.append(it)
            elif (mode == 'movie' and it.contentTitle) or (mode == 'tvshow' and (it.contentSerieName or it.show)):
                grouped.append(it)
            else:
                continue

        if not grouped:
            continue
        # to_temp[key] = grouped

        if not config.get_setting('unify'):
            title = typo('%s %s' % (len(grouped), config.get_localized_string(70695)), 'bold') + typo(key,'_ [] color kod bold')
        else:
            title = typo('%s %s' % (len(grouped), config.get_localized_string(70695)), 'bold')
        res_count += len(grouped)
        plot=''
        for it in grouped:
            plot += it.title +'\n'
        ch_thumb = channeltools.get_channel_parameters(key)['thumbnail']
        results.append(Item(channel='search', title=title,
                            action='get_from_temp', thumbnail=ch_thumb, itemlist=[ris.tourl() for ris in grouped], plot=plot, page=1))

    results = sorted(results, key=lambda it: it.from_channel)

    # send_to_temp(to_temp)
    config.set_setting('tmdb_active', True)
    results_statistic = config.get_localized_string(59972) % (item.title, res_count, time.time() - start)
    results.insert(0, Item(title = typo(results_statistic,'color kod bold')))
    logger.debug(results_statistic)

    return valid + results


def get_channel_results(ch, item, session):
    max_results = 10
    results = list()

    ch_params = channeltools.get_channel_parameters(ch)

    exec "from channels import " + ch_params["channel"] + " as module"

    mainlist = module.mainlist(Item(channel=ch_params["channel"]))
    search_action = [elem for elem in mainlist if elem.action == "search" and (item.mode == 'all' or elem.contentType == item.mode)]

    if search_action:
        for search_ in search_action:
            search_.session = session
            try:
                results.extend(module.search(search_, item.text))
            except:
                pass
    else:
        try:
            results.extend(module.search(item, item.text))
        except:
            pass

    if len(results) < 0 and len(results) < max_results and item.mode != 'all':

        if len(results) == 1:
            if not results[0].action or config.get_localized_string(30992).lower() in results[0].title.lower():
                return [ch, []]

        results = get_info(results)

    return [ch, results]


def get_info(itemlist):
    logger.info()
    tmdb.set_infoLabels_itemlist(itemlist, True, forced=True)

    return itemlist


def get_channels(item):
    logger.info()

    channels_list = list()
    all_channels = channelselector.filterchannels('all')

    for ch in all_channels:
        channel = ch.channel
        ch_param = channeltools.get_channel_parameters(channel)
        if not ch_param.get("active", False):
            continue
        list_cat = ch_param.get("categories", [])

        if not ch_param.get("include_in_global_search", False):
            continue

        if 'anime' in list_cat:
            n = list_cat.index('anime')
            list_cat[n] = 'tvshow'

        if item.mode == 'all' or (item.mode in list_cat):
            if config.get_setting("include_in_global_search", channel):
                channels_list.append(channel)

    return channels_list


def opciones(item):
    return setting_channel_new(item)


def setting_channel_new(item):
    import xbmcgui

    # Load list of options (active user channels that allow global search)
    lista = []
    ids = []
    lista_lang = []
    lista_ctgs = []
    channels_list = channelselector.filterchannels('all')
    for channel in channels_list:
        if channel.action == '':
            continue

        channel_parameters = channeltools.get_channel_parameters(channel.channel)

        # Do not include if "include_in_global_search" does not exist in the channel configuration
        if not channel_parameters['include_in_global_search']:
            continue

        lbl = '%s' % channel_parameters['language']
        lbl += ' %s' % ', '.join(config.get_localized_category(categ) for categ in channel_parameters['categories'])

        it = xbmcgui.ListItem(channel.title, lbl)
        it.setArt({'thumb': channel.thumbnail, 'fanart': channel.fanart})
        lista.append(it)
        ids.append(channel.channel)
        lista_lang.append(channel_parameters['language'])
        lista_ctgs.append(channel_parameters['categories'])

    # Pre-select dialog
    preselecciones = [
        config.get_localized_string(70570),
        config.get_localized_string(70571),
        # 'Modificar partiendo de Recomendados',
        # 'Modificar partiendo de Frecuentes',
        config.get_localized_string(70572),
        config.get_localized_string(70573),
        # 'Modificar partiendo de Castellano',
        # 'Modificar partiendo de Latino'
    ]
    # presel_values = ['skip', 'actual', 'recom', 'freq', 'all', 'none', 'cast', 'lat']
    presel_values = ['skip', 'actual', 'all', 'none']

    categs = ['movie', 'tvshow', 'documentary', 'anime', 'vos', 'direct', 'torrent']
    if config.get_setting('adult_mode') > 0:
        categs.append('adult')
    for c in categs:
        preselecciones.append(config.get_localized_string(70577) + config.get_localized_category(c))
        presel_values.append(c)

    if item.action == 'setting_channel':  # Configuración de los canales incluídos en la búsqueda
        del preselecciones[0]
        del presel_values[0]
    # else: # Call from "search on other channels" (you can skip the selection and go directly to the search)

    ret = platformtools.dialog_select(config.get_localized_string(59994), preselecciones)
    if ret == -1:
        return False  # order cancel
    if presel_values[ret] == 'skip':
        return True  # continue unmodified
    elif presel_values[ret] == 'none':
        preselect = []
    elif presel_values[ret] == 'all':
        preselect = range(len(ids))
    elif presel_values[ret] in ['cast', 'lat']:
        preselect = []
        for i, lg in enumerate(lista_lang):
            if presel_values[ret] in lg or '*' in lg:
                preselect.append(i)
    elif presel_values[ret] == 'actual':
        preselect = []
        for i, canal in enumerate(ids):
            channel_status = config.get_setting('include_in_global_search', canal)
            if channel_status:
                preselect.append(i)

    elif presel_values[ret] == 'recom':
        preselect = []
        for i, canal in enumerate(ids):
            _not, set_canal_list = channeltools.get_channel_controls_settings(canal)
            if set_canal_list.get('include_in_global_search', False):
                preselect.append(i)

    elif presel_values[ret] == 'freq':
        preselect = []
        for i, canal in enumerate(ids):
            frequency = channeltools.get_channel_setting('frequency', canal, 0)
            if frequency > 0:
                preselect.append(i)
    else:
        preselect = []
        for i, ctgs in enumerate(lista_ctgs):
            if presel_values[ret] in ctgs:
                preselect.append(i)

    # Dialog to select
    ret = xbmcgui.Dialog().multiselect(config.get_localized_string(59994), lista, preselect=preselect, useDetails=True)
    if not ret:
        return False  # order cancel
    seleccionados = [ids[i] for i in ret]

    # Save changes to search channels
    for canal in ids:
        channel_status = config.get_setting('include_in_global_search', canal)
        # if not channel_status:
        #     channel_status = True

        if channel_status and canal not in seleccionados:
            config.set_setting('include_in_global_search', False, canal)
        elif not channel_status and canal in seleccionados:
            config.set_setting('include_in_global_search', True, canal)

    return True


def genres_menu(item):
    itemlist = []
    mode = item.mode.replace('show', '')

    genres = tmdb.get_genres(mode)
    for key, value in genres[mode].items():
        discovery = {'url': 'discover/%s' % mode, 'with_genres': key,
                     'language': def_lang, 'page': '1'}

        itemlist.append(Item(channel=item.channel, title=typo(value, 'bold'), page=1,
                             action='discover_list', discovery=discovery,
                             mode=item.mode))
    channelselector.thumb(itemlist)
    return sorted(itemlist, key=lambda it: it.title)


def years_menu(item):
    import datetime
    itemlist = []

    mode = item.mode.replace('show', '')

    par_year = 'primary_release_year'
    thumb = channelselector.get_thumb('channels_movie_year.png')

    if mode != 'movie':
        par_year = 'first_air_date_year'
        thumb = channelselector.get_thumb('channels_tvshow_year.png')

    c_year = datetime.datetime.now().year + 1
    l_year = c_year - 31

    for year in range(l_year, c_year):
        discovery = {'url': 'discover/%s' % mode, 'page': '1',
                     '%s' % par_year: '%s' % year,
                     'sort_by': 'popularity.desc', 'language': def_lang}

        itemlist.append(Item(channel=item.channel, title=typo(str(year), 'bold'), action='discover_list',
                             discovery=discovery, mode=item.mode, year_=str(year), thumbnail=thumb))
    itemlist.reverse()
    itemlist.append(Item(channel=item.channel, title=typo(config.get_localized_string(70745),'color kod bold'), url='',
                         action="year_cus", mode=item.mode, par_year=par_year))

    return itemlist


def year_cus(item):
    mode = item.mode.replace('show', '')

    heading = config.get_localized_string(70042)
    year = platformtools.dialog_numeric(0, heading, default="")
    item.discovery = {'url': 'discover/%s' % mode, 'page': '1',
                      '%s' % item.par_year: '%s' % year,
                      'sort_by': 'popularity.desc', 'language': def_lang}
    item.action = "discover_list"
    if year and len(year) == 4:
        return discover_list(item)


def actor_list(item):
    itemlist = []

    dict_ = {'url': 'search/person', 'language': def_lang, 'query': item.searched_text, 'page': item.page}

    prof = {'Acting': 'Actor', 'Directing': 'Director', 'Production': 'Productor'}
    plot = ''
    item.search_type = 'person'

    tmdb_inf = tmdb.discovery(item, dict_=dict_)
    results = tmdb_inf.results

    if not results:
        return results

    for elem in results:
        name = elem.get('name', '')
        if not name:
            continue

        rol = elem.get('known_for_department', '')
        rol = prof.get(rol, rol)
        # genero = elem.get('gender', 0)
        # if genero == 1 and rol in prof:
        #     rol += 'a'
        #     rol = rol.replace('Actora', 'Actriz')

        know_for = elem.get('known_for', '')
        cast_id = elem.get('id', '')
        if know_for:
            t_k = know_for[0].get('title', '')
            if t_k:
                plot = '%s in %s' % (rol, t_k)

        thumbnail = 'http://image.tmdb.org/t/p/original%s' % elem.get('profile_path', '')
        title = typo(name,'bold')+typo(rol,'_ [] color kod bold')

        discovery = {'url': 'person/%s/combined_credits' % cast_id, 'page': '1',
                     'sort_by': 'primary_release_date.desc', 'language': def_lang}

        itemlist.append(Item(channel=item.channel, title=title, action='discover_list', cast_='cast',
                             discovery=discovery, thumbnail=thumbnail, plot=plot, page=1))

    if len(results) > 19:
        next_ = item.page + 1
        itemlist.append(Item(channel=item.channel, title=typo(config.get_localized_string(30992),'bold color kod'), action='actor_list',
                             page=next_, thumbnail=thumbnail,
                             searched_text=item.searched_text))
    return itemlist


def discover_list(item):
    import datetime
    itemlist = []

    year = 0
    tmdb_inf = tmdb.discovery(item, dict_=item.discovery, cast=item.cast_)
    result = tmdb_inf.results
    tvshow = False

    for elem in result:
        elem = tmdb_inf.get_infoLabels(elem, origen=elem)
        if 'title' in elem:
            title = unify.normalize(elem['title']).capitalize()
        else:
            title = unify.normalize(elem['name']).capitalize()
            tvshow = True
        elem['tmdb_id'] = elem['id']

        mode = item.mode or elem['media_type']
        thumbnail = elem.get('thumbnail', '')
        fanart = elem.get('fanart', '')

        if item.cast_:
            release = elem.get('release_date', '0000') or elem.get('first_air_date', '0000')
            year = scrapertools.find_single_match(release, r'(\d{4})')

        if not item.cast_ or (item.cast_ and (int(year) <= int(datetime.datetime.today().year))):
            new_item = Item(channel='search', title=typo(title, 'bold'), infoLabels=elem,
                            action='channel_search', text=title,
                            thumbnail=thumbnail, fanart=fanart,
                            context='', mode=mode,
                            release_date=year)

            if tvshow:
                new_item.contentSerieName = title
            else:
                new_item.contentTitle = title

            itemlist.append(new_item)

    itemlist = set_context(itemlist)

    if item.cast_:
        itemlist.sort(key=lambda it: int(it.release_date), reverse=True)
        return itemlist

    elif len(result) > 19 and item.discovery:
        item.discovery['page'] = str(int(item.discovery['page']) + 1)
        itemlist.append(Item(channel=item.channel, action='discover_list', title=config.get_localized_string(70065),
                             list_type=item.list_type, discovery=item.discovery, text_color='gold'))
    elif len(result) > 19:
        next_page = str(int(item.page) + 1)

        itemlist.append(Item(channel=item.channel, action='discover_list', title=config.get_localized_string(70065),
                             list_type=item.list_type, search_type=item.search_type, mode=item.mode, page=next_page,
                             text_color='gold'))

    return itemlist


def from_context(item):
    logger.info()

    select = setting_channel_new(item)

    if not select:
        return

    if 'infoLabels' in item and 'mediatype' in item.infoLabels:
        item.mode = item.infoLabels['mediatype']
    else:
        return

    if 'list_type' not in item:
        if 'wanted' in item:
            item.title = item.wanted
        return channel_search(item)

    return discover_list(item)


def set_context(itemlist):
    logger.info()

    for elem in itemlist:
        elem.context = [{"title": config.get_localized_string(60412),
                         "action": "setting_channel_new",
                         "channel": "search"}]

    return itemlist


def get_from_temp(item):
    logger.info()

    n = 30
    nTotal = len(item.itemlist)
    nextp = n * item.page
    prevp = n * (item.page - 1)

    results = [Item().fromurl(elem) for elem in item.itemlist[prevp:nextp]]

    if nextp < nTotal:
        results.append(Item(channel='search', title=typo(config.get_localized_string(30992),'bold color kod'),
                            action='get_from_temp', itemlist=item.itemlist, page=item.page + 1))

    tmdb.set_infoLabels_itemlist(results, True)
    for elem in results:
        if not elem.infoLabels.get('year', ""):
            elem.infoLabels['year'] = '-'
            tmdb.set_infoLabels_item(elem, True)

    return results