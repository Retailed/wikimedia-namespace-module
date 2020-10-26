import mwapi     # using mediawiki library for making requests
import sqlite3

SITENAME: str = 'https://en.wikipedia.org/'


def init_database():
    conn = sqlite3.connect('namespace-modules.db')
    cursor = conn.cursor()
    cursor.execute('''create table modulesData 
                        (pageid integer unique, 
                        title text,
                        sourcecode text)''')
    cursor.execute('insert into modulesData values (1, "F", "F")')
    conn.commit()

    cursor.execute('select * from modulesData')
    print(cursor.fetchall())

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
              'aplimit': 'max',        # letting the request get first 500 pages
              'maxlag': '3',           # waiting about 3 seconds is ok if needed
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
              'formatversion': '2',
              'maxlag': '1'}           # adding lag to help server a bit

    request = session.get(params)

    wikitext = False
    if 'parse' in request:
        wikitext = request['parse']['wikitext']

    return wikitext



if __name__ == "__main__":
    session = mwapi.Session(SITENAME, user_agent="LostEnchanter")
    continue_addr = 'AAAA'             # we know, that the 1st apcontinue is "bigger"

    while continue_addr:
        if continue_addr == 'AAAA':
            request_data = get_pages_data(session)
        else:
            request_data = get_pages_data(session, continue_addr)

        basic_pages_data, continue_addr = parse_pages_data(request_data)

        # add sourcecode to existing data
        for i, elem in enumerate(basic_pages_data):
            sourcecode = get_parse_page_soursecode(session, elem[0])
            basic_pages_data[i].append(sourcecode)



    print('all')

