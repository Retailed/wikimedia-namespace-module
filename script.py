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


def get_data():
    session = mwapi.Session(SITENAME, user_agent="LostEnchanter")
    params = {'action': 'query',
              'format': 'json',
              'list': 'allpages',
              'apnamespace': '828',    # https://en.wikipedia.org/wiki/Special:PrefixIndex?prefix=&namespace=828
              'aplimit': 'max',        # letting the request get first 500 pages
              'maxlag': '3'}           # waiting about 3 seconds is ok if needed

    request_data = session.get(params)
    print('Done')

if __name__ == "__main__":
    init_database()
