from common import UserAgent

def main():
    ua = UserAgent(limit=10, operating_systems=['windows', 'linux'])
    # print(ua.get_user_agents())
    print(ua.get_random_user_agent())

if __name__ == '__main__':
    main()
