class DBNotAvailable(Exception):
    def __str__(self):
        return "ERROR! There is no database available."
