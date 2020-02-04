class MemoryStorage:
    """This is a substitute storage for Framework that only writes to memory.

    It is not safe to use in production code, as all state is lost when the
    process exits, but is useful for test cases.
    """

    def __init__(self):
        self._snapshots = {}
        self._notices = []

    def close(self):
        pass

    def commit(self):
        pass

    def save_snapshot(self, handle_path, snapshot_data):
        self._snapshots[handle_path] = snapshot_data

    def load_snapshot(self, handle_path):
        return self._snapshots.get(handle_path, None)

    def drop_snapshot(self, handle_path):
        self._snapshots.pop(handle_path, None)

    def save_notice(self, event_path, observer_path, method_name):
        self._notices.append((event_path, observer_path, method_name))

    def drop_notice(self, event_path, observer_path, method_name):
        key = (event_path, observer_path, method_name)
        try:
            del self._notices[self._notices.index(key)]
        except ValueError:
            pass

    def notices(self, event_path):
        # grab a local copy, because emitting a notice may cause it to be deleted afterward
        notices = self._notices[:]
        if event_path:
            out = []
            for notice in notices:
                if notice[0] == event_path:
                    #print(f'emitting {notice}')
                    yield notice
                # else:
                #    print(f'skipping {notice}')
        else:
            for notice in notices:
                yield notice
