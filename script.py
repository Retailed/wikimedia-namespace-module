import mwapi  # using mediawiki library for making requests
from mwapi.errors import APIError
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as st

DATABASE_NAME: str = 'namespace-modules.db'
OUTREACHY_INFO: str = 'LostEnchanter Outreachy round 21'
SITENAME: str = 'https://en.wikipedia.org/'


def database_init():
    """
    Create table for storing sourcecode if needed.

    :return: empty
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''create table if not exists modulesData 
                        (pageid integer unique, 
                        title text,
                        sourcecode text)''')
    conn.commit()
    conn.close()


def database_drop():
    """
    Drops table for sourcecode if it exists.

    :return: empty
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('drop table if exists modulesData')
    conn.commit()
    conn.close()


def database_fill_pages_basic_data(pages_data):
    """
    Bulk insert parsed ids and titles into table.

    :param pages_data: array of arrays
        data from parsed api requests
    :return: empty
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.executemany('INSERT INTO modulesData VALUES (?, ?, NULL)', pages_data)
    conn.commit()
    conn.close()


def database_get_ids_without_sources():
    """
    Get all page ids, where the sourcecode wasn't loaded previously.
    (or is empty, as we can't differentiate)

    :return: array of tuples with ids without sourcecode
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('select pageid from modulesData where sourcecode is NULL')
    res = cursor.fetchall()
    conn.close()
    return res


def database_set_sourcecode(id, sourcetext):
    """
    Save sourcecode to the page with chosen id.

    :param id: string
        page id
    :param sourcetext: string
        sourcecode of the page, obtained by parse request
    :return: empty
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('update modulesData set sourcecode = ? where pageid = ?', (sourcetext, id))
    conn.commit()
    conn.close()


def database_get_ids():
    """
    Get ids of all the pages, stored in modulesData.

    :return: array of tuples with ids
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('select pageid from modulesData')
    res = cursor.fetchall()
    conn.close()
    return res


def database_get_all_pages_info():
    """
    Get interesting data of all the pages, stored in modulesData.

    :return: array of tuples with info (title, contentmodel, touched, length)
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('select title, contentmodel, touched, len from modulesData where len is not NULL')
    res = cursor.fetchall()
    conn.close()
    return res


def database_expand_table():
    """
    Create columns for additional info about loaded pages.

    :return: empty
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('alter table modulesData add column contentmodel text')
    cursor.execute('alter table modulesData add column touched numeric')
    cursor.execute('alter table modulesData add column len integer')
    conn.commit()
    conn.close()


def database_set_additional_info(pages_info):
    """
    Update page info with additional data (contentmodel, touched and length)

    :param pages_info: array of arrays
        structure: [contentmodel, touched, length, pageid]
    :return: empty
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.executemany('update modulesData '
                       'set contentmodel = ?, touched = ?, len = ?'
                       'where pageid = ?', pages_info)
    conn.commit()
    conn.close()


def get_pages_data(session, continue_addr=''):
    """
    Makes allpages request in namespace to get pages info.

    :param session: mwapi.Session
        connection to wikipedia api through mwapi
    :param continue_addr: string, optional
         apcontinue for loading info past aplimit
    :return: json-formatted request answer
    """
    params = {'action': 'query',
              'format': 'json',
              'list': 'allpages',
              'apnamespace': '828',  # https://en.wikipedia.org/wiki/Special:PrefixIndex?prefix=&namespace=828
              'aplimit': '500',  # letting the request get 500 pages
              'apcontinue': continue_addr}

    request_data = session.get(params)
    return request_data


def parse_pages_data(request):
    """
    Parses allpages request to get basic info of module: namespace pages and apcontinue.

    :param request: json request from get_pages_data
    :return: parsed ids and titles of pages and apcontinue if exists
    """
    continue_addr = False
    if 'continue' in request:
        continue_addr = request['continue']['apcontinue']
    pages_data = []
    for elem in request['query']['allpages']:
        pages_data.append([elem['pageid'], elem['title']])

    return pages_data, continue_addr


def get_parse_page_sourcecode(session, page_id):
    """
    Request and parse sourcecode of page with chosen id

    :param session: wapi.Session
        connection to wikipedia api through mwapi
    :param page_id: str
        id of requested page
    :return: string, containing the sourcecode of chosen page
    """
    params = {'action': 'parse',
              'format': 'json',
              'pageid': page_id,
              'prop': 'wikitext',  # saving in wikitext as it's more readable than html
              'formatversion': '2'}  # adding lag to help server a bit

    try:
        request = session.get(params)

        wikitext = False
        if 'parse' in request:
            wikitext = request['parse']['wikitext']

        return wikitext
    except APIError as error:
        print("MediaWiki returned an error:" + str(error))
        return None


def get_parse_additional_data(session, page_ids):
    """
    Request additional page info for chosen ids and parse obtained json.

    :param session: wapi.Session
        connection to wikipedia api through mwapi
    :param page_ids: array of tuples with ids
    :return: array of arrays
        each array stores contentmodel, touched and length fields for id
    """
    ids_string = str(page_ids[0][0])
    for elem in page_ids:
        ids_string += "|" + str(elem[0])

    params = {'action': 'query',
              'format': 'json',
              'pageids': ids_string,
              'prop': 'info',
              'inprop': 'protection'}

    request_data = session.get(params)

    pages_data = []
    elem = request_data['query']['pages']
    for curr_id in page_ids:
        if 'missing' not in elem[str(curr_id[0])]:
            pages_data.append([elem[str(curr_id[0])]['contentmodel'],
                               elem[str(curr_id[0])]['touched'],
                               elem[str(curr_id[0])]['length'],
                               str(curr_id[0])])

    return pages_data


def statistics_contentmodel(contentmodels):
    """
    Draws horizontal bar chart based on contentmodels of saved pages.

    :param contentmodels: array of strings,
        contentmodel field data
    :return: empty
    """

    fig, ax = plt.subplots()

    contentmodel_types = list(set(contentmodels))       # as set is unordered
    y_pos = np.arange(len(contentmodel_types))
    amount = [contentmodels.count(elem) for elem in contentmodel_types]

    # adding amount of elements to axis labels
    for i, elem in enumerate(contentmodel_types):
        contentmodel_types[i] = elem + "\n(" + str(amount[i]) + ")"

    ax.barh(y_pos, amount, align='center', log="True")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(contentmodel_types)
    ax.set_xlabel('Amount')
    ax.set_title('Contentmodel types in pages')

    plt.show()


def statistics_length(lengths):
    """
    Shows some statistics about lengths array:\n
    - minimum, maximum and mean length;\n
    - draws histogram based on pages lengths given.\n

    :param lengths:array of integers,
        length field data
    :return: empty
    """
    print('Maximum source code length - {:d} symbols ({:d} case(s))\n'
          'Minimal source code length - {:d} symbols ({:d} case(s))\n'
          'Mean source code length - {:d} symbols'.format(
                max(lengths), lengths.count(max(lengths)),
                min(lengths), lengths.count(min(lengths)), round(np.mean(lengths))))

    plt.hist(lengths, bins='sturges', log=True, histtype='stepfilled')
    plt.ylabel('Amount of pages')
    plt.xlabel('Source length in symbols')
    plt.title('Histogram of the lengths of sourcecode')

    plt.show()


def modules_fill_basic_table():
    """
    Module for creating table in database and getting ids of pages from namespace.

    :return: empty
    """
    database_drop()
    database_init()
    session = mwapi.Session(SITENAME, user_agent=OUTREACHY_INFO)
    continue_addr = 'AAAA'  # we know, that the 1st apcontinue is "bigger"

    while continue_addr:
        if continue_addr == 'AAAA':
            request_data = get_pages_data(session)
        else:
            request_data = get_pages_data(session, continue_addr)

        basic_pages_data, continue_addr = parse_pages_data(request_data)
        database_fill_pages_basic_data(basic_pages_data)


def modules_load_sources():
    """
    Module for loading sourcecode of pages listed in database.

    :return: empty
    """
    session = mwapi.Session(SITENAME, user_agent=OUTREACHY_INFO)
    sourceless = database_get_ids_without_sources()
    failed = 0
    for elem in sourceless:
        source = get_parse_page_sourcecode(session, elem[0])
        if not source:
            failed += 1
        else:
            database_set_sourcecode(elem[0], source)

    print("Sources failed to load: " + str(failed))


def modules_load_additional_data():
    """
    Module for loading additional info (fields contentmodel, touched, length)
     of pages listed in database.

    :return: empty
    """
    database_expand_table()

    session = mwapi.Session(SITENAME, user_agent=OUTREACHY_INFO)
    ids = database_get_ids()

    stepsize = 25
    for i in range(0, len(ids), stepsize):
        pages_data = get_parse_additional_data(session, ids[i:i + stepsize])
        database_set_additional_info(pages_data)


def modules_statistics():
    """
    Module for generating some statistics based on info from database

    :return: empty
    """
    res = database_get_all_pages_info()

    print('Amount of pages in Module:namespace - {:d}'.format(len(res)))

    titles = [elem[0] for elem in res]
    contentmodels = [elem[1] for elem in res]
    touched_dates = [elem[2] for elem in res]
    lengths = [elem[-1] for elem in res]

    statistics_contentmodel(contentmodels)
    statistics_length(lengths)


if __name__ == "__main__":
    modules_statistics()
