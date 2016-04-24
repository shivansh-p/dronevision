# common
import logging

# other
import shapefile
from pyelasticsearch import ElasticSearch, ElasticHttpError

logging.basicConfig()
logging.getLogger('elasticsearch.trace').setLevel(logging.INFO)
logging.getLogger('elasticsearch').setLevel(logging.INFO)


ELASTICSEARCH_HOST = 'http://elasticsearch:9200/'
ELASTICSEARCH_INDEX = 'library'
ELASTICSEARCH_DOC = 'zones'


es = ElasticSearch(ELASTICSEARCH_HOST, timeout=120)


FILES = [
    "nofly/shapefile/us_national_parks",
    "nofly/shapefile/us_military",
    "nofly/shapefile/5_mile_airport",
]

try:
    es.delete_all(ELASTICSEARCH_DOC, ELASTICSEARCH_INDEX)
except ElasticHttpError:
    pass

try:
    es.delete_index(ELASTICSEARCH_INDEX)
except ElasticHttpError:
    pass

index_settings = {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "mappings": {
        ELASTICSEARCH_DOC: {
            "properties": {
                "location": {
                    "type": "geo_shape",
                    "tree": "quadtree",
                    "precision": "1m"
                }
            }
        },
    }
}
es.create_index(ELASTICSEARCH_INDEX, settings=index_settings)

for filename in FILES:
    print "Processing %s" % filename

    sf = shapefile.Reader(filename)

    shapes = sf.shapes()
    for i, shape in enumerate(shapes, start=1):
        points = [(p[0], p[1]) for p in shape.points]

        data = {
            'filename': filename,
            'location': {
                'type': 'polygon',
                'coordinates': [points]
            }
        }

        if points[-1] != points[0]:
            points.append(points[0])

        try:
            es.bulk([es.index_op(data)],
                    doc_type=ELASTICSEARCH_DOC,
                    index=ELASTICSEARCH_INDEX)
        except:
            print "Exception"
