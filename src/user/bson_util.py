
def convert_id(collection) :
    return list(map(lambda d: {**d, "_id": str(d["_id"])}, collection))
