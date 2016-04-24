# common
import logging

# django
from django.conf import settings

# other
import shapefile
from pyelasticsearch import ElasticSearch, ElasticHttpError

logging.basicConfig()
logging.getLogger('elasticsearch.trace').setLevel(logging.INFO)
logging.getLogger('elasticsearch').setLevel(logging.INFO)


INIT = False
es = ElasticSearch(settings.ELASTICSEARCH_HOST, timeout=120)


if INIT:
    FILES = [
        "nofly/shapefile/us_national_parks",
        "nofly/shapefile/us_military",
        "nofly/shapefile/5_mile_airport",
    ]

    c = (34.0572105135103, -118.70590209960938)

    try:
        es.delete_all(settings.ELASTICSEARCH_DOC, settings.ELASTICSEARCH_INDEX)
    except ElasticHttpError:
        pass

    try:
        es.delete_index(settings.ELASTICSEARCH_INDEX)
    except ElasticHttpError:
        pass

    settings = {
        "number_of_shards": 3,
        "number_of_replicas": 1,
        "mappings": {
            settings.ELASTICSEARCH_DOC: {
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
    es.create_index(settings.ELASTICSEARCH_INDEX, settings=settings)

    for filename in FILES:
        print "Processing %s" % filename

        sf = shapefile.Reader(filename)

        shapes = sf.shapes()
        indexes = []
        for i, shape in enumerate(shapes, start=1):
            points = [(p[0], p[1]) for p in shape.points]

            data = {
                'filename': filename,
                'location': {
                    'type': 'polygon',
                    'coordinates': [points]
                }
            }
            #indexes.append(es.index_op(data))

            #for chunk in chunker(indexes, 10):
            if points[-1] != points[0]:
                points.append(points[0])

            try:
                es.bulk([es.index_op(data)],
                        doc_type=settings.ELASTICSEARCH_DOC,
                        index=settings.ELASTICSEARCH_INDEX)
            except:
                print "Exception"
