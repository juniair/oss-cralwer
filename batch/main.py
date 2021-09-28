import sys
from clare import Clare
import traceback


if __name__ == "__main__":

    release_id_range = (None, None)
    try:
        if 3 <= len(sys.argv):
            start_release_id = int(sys.argv[1])
            last_release_id = int(sys.argv[2])
            release_id_range = (start_release_id, last_release_id)
        batch = Clare(True)
        batch.run(release_id_range)
    except Exception as e:
        print(e)
        traceback.print_exc()
