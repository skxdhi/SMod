class list_all(list):
    def __init__(self):
        super().__init__()

    def __contains__(self, item):
        return True

class tuple_all(tuple):
    def __init__(self):
        super().__init__()

    def __contains__(self, item):
        return True