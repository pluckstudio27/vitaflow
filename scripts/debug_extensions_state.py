import json
import extensions
print(json.dumps({'mongo_db_is_set': extensions.mongo_db is not None}))