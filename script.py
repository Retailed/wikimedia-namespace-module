import mwapi     # using mediawiki library for making requests
from mwapi.errors import APIError
import sqlite3

SITENAME: str = 'https://en.wikipedia.org/'


def database_init():
    '''
    Create table for storing soursecodes if needed.

    :return: empty
    '''
    conn = sqlite3.connect('namespace-modules.db')
    cursor = conn.cursor()
    cursor.execute('''create table if not exists modulesData 
                        (pageid integer unique, 
                        title text,
                        sourcecode text)''')
    conn.commit()
    conn.close()


def database_drop():
    '''
    Drops table for soursecodes if it exists.

    :return: empty
    '''
    conn = sqlite3.connect('namespace-modules.db')
    cursor = conn.cursor()
    cursor.execute('drop table if exists modulesData')
    conn.commit()
    conn.close()


def database_fill_pages_basic_data(pages_data):
    '''
    Bulk insert parsed ids and titles into table.

    :param pages_data: array of arrays
        data from parsed api requests
    :return: empty
    '''
    conn = sqlite3.connect('namespace-modules.db')
    cursor = conn.cursor()
    cursor.executemany('INSERT INTO modulesData VALUES (?, ?, NULL)', pages_data)
    conn.commit()
    conn.close()


def database_get_ids_without_sourses():
    conn = sqlite3.connect('namespace-modules.db')
    cursor = conn.cursor()
    cursor.execute('select pageid from modulesData where sourcecode is NULL')
    res = cursor.fetchall()
    conn.close()
    return res


def database_set_soursecode(id, sourcetext):
    conn = sqlite3.connect('namespace-modules.db')
    cursor = conn.cursor()
    cursor.execute('update modulesData set sourcecode = ? where pageid = ?', (sourcetext, id))
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
              'apnamespace': '828',    # https://en.wikipedia.org/wiki/Special:PrefixIndex?prefix=&namespace=828
              'aplimit': '500',        # letting the request get 500 pages
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


def get_parse_page_soursecode(session, page_id):
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
              'prop': 'wikitext',      # saving in wikitext as it's more readable than html
              'formatversion': '2'}    # adding lag to help server a bit

    try:
        request = session.get(params)

        wikitext = False
        if 'parse' in request:
            wikitext = request['parse']['wikitext']

        return wikitext
    except APIError as error:
        print("MediaWiki returned an error:" + str(error))
        return None


def modules_fill_basic_table():
    database_drop()
    database_init()
    session = mwapi.Session(SITENAME, user_agent="LostEnchanter Outreachy round 21")
    continue_addr = 'AAAA'             # we know, that the 1st apcontinue is "bigger"

    while continue_addr:
        if continue_addr == 'AAAA':
            request_data = get_pages_data(session)
        else:
            request_data = get_pages_data(session, continue_addr)

        basic_pages_data, continue_addr = parse_pages_data(request_data)

        print('basic data collected')

        database_fill_pages_basic_data(basic_pages_data)

        print('next batch')




def modules_load_sourses():
    session = mwapi.Session(SITENAME, user_agent="LostEnchanter Outreachy round 21")
    sourceless = database_get_ids_without_sourses()
    failed = 0
    for elem in sourceless:
        source = get_parse_page_soursecode(session, elem[0])
        if not source:
            failed += 1
        else:
            database_set_soursecode(elem[0], source)

    print("Sources failed to load: " + str(failed))


if __name__ == "__main__":
    modules_load_sourses()

