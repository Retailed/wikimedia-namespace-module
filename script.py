import mwapi     # using mediawiki library for making requests


SITENAME: str = 'https://en.wikipedia.org/'


def get_data():

    session = mwapi.Session(SITENAME, user_agent="LostEnchanter")
    print(session.get(action='query', meta='userinfo'))


if __name__ == "__main__":
    get_data()
