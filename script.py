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
    print('Done')
    return request_data


def parse_pages_data(request):
    """
    Parses allpages request to get basic info of module: namespace pages and apcontinue.

    :param request: json request from get_pages_data
    :return: parsed ids and titles of pages and apcontinue if exists
    """
    continue_addr = request['continue']['apcontinue']
    pages_data = []
    for elem in request['query']['allpages']:
        pages_data.append([elem['pageid'], elem['title']])

    return pages_data, continue_addr



if __name__ == "__main__":
    session = mwapi.Session(SITENAME, user_agent="LostEnchanter")
    request_data = get_pages_data(session)
    basic_pages_data, continue_addr = parse_pages_data(request_data)


