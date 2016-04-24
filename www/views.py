# -*- coding: utf-8 -*-

# common
import time
import math
import logging
import hashlib

# django
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.cache import cache

# other
import googlemaps
from googlemaps import elevation
from pyelasticsearch import ElasticSearch

from geopy.distance import VincentyDistance, vincenty
import geopy

# my
from models import Token, Track


class JSONResponseMixin(object):
    def render_to_json_response(self, **response_kwargs):
        return JsonResponse(
            self.get_data(**response_kwargs)
        )

    def get_data(self, **response_kwargs):
        return {}

    @property
    def REQUEST(self):
        return self.request.GET or self.request.POST


class JSONView(JSONResponseMixin, View):
    def get(self, request, *args, **kwargs):
        return self.render_to_json_response(**kwargs)

    def post(self, request, *args, **kwargs):
        return self.render_to_json_response(**kwargs)

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(JSONView, self).dispatch(*args, **kwargs)


class HomeView(TemplateView):
    template_name = "home.html"


class MapView(TemplateView):
    template_name = "map.html"

    def get_context_data(self, **kwargs):
        es = ElasticSearch(settings.ELASTICSEARCH_HOST)
        return {
            'query': es.search()
        }


class CreateTrackApiView(JSONView):
    def get_data(self, **response_kwargs):
        track = Track()
        track.save()
        return track.dict()


class UpadateTrackApiView(JSONView):
    def get_data(self, track_id):
        track = get_object_or_404(Track, id=track_id)
        lat = float(self.REQUEST.get('lat'))
        lng = float(self.REQUEST.get('lng'))
        alt = float(self.REQUEST.get('alt'))
        METERS_LOOK = int(self.REQUEST.get('look_ahead', 100))
        RADIUS = float(self.REQUEST.get('radius', 8000))
        assert lat and lng and alt

        point = {
            'lat': lat,
            'lng': lng,
            'alt': alt,
            'time': time.time(),
        }

        if not track.points:
            track.points = []
        track.points.append(point)
        track.save()

        latest_point, latest_time = track.get_point(0)
        prev_point = None
        prev_time = None
        if latest_point:
            current_index = 1
            while True:
                prev_point, prev_time = track.get_point(current_index)
                if not prev_point:
                    break

                d = vincenty(prev_point, latest_point)
                if d.meters > 0.01:
                    break

                current_index += 1

        advices = []
        speed = 0
        angle = 0
        terrain = {
            'highest_point': None,
            'distance_to_highest_point': None,
        }
        gmaps = googlemaps.Client(key=settings.MAPS_GOOGLE_KEY)
        if latest_point and prev_point:
            terrain['highest_point'] = 0
            terrain['distance_to_highest_point'] = 0

            bearing = calculate_initial_compass_bearing(prev_point, latest_point)

            origin = geopy.Point(latest_point[0], latest_point[1])
            destination = VincentyDistance(meters=METERS_LOOK).destination(origin, bearing)

            point100 = destination.latitude, destination.longitude

            rs = get_elevation_path(gmaps, [latest_point, point100], METERS_LOOK)

            for i, r in enumerate(rs):
                elev = r['elevation']
                if not i or terrain['highest_point'] < elev:
                    terrain['highest_point'] = elev
                    terrain['distance_to_highest_point'] = i + 1

                if alt < elev:
                    break

            if terrain['highest_point'] >= alt:
                advices.append({
                    'type': 'critical',
                    'message': 'After %s metres you will strike terrain' % terrain['distance_to_highest_point'],
                })

            d = vincenty(latest_point, prev_point).meters
            t = (latest_time - prev_time)
            if t > 0:
                speed = d / t

            angle = bearing

        search = {
            'query': {
                'geo_shape': {
                    "location": {
                        "relation": "intersects",
                        "shape": {
                            "type": "circle",
                            "radius": "%sm" % RADIUS,
                            "coordinates": [
                                latest_point[1], latest_point[0],
                            ],
                        }
                    }
                }
            }
        }

        es = ElasticSearch(settings.ELASTICSEARCH_HOST)
        eresults = es.search(search, doc_type=settings.ELASTICSEARCH_DOC, index=settings.ELASTICSEARCH_INDEX)
        inserctions = eresults.get('hits', [])

        rs = get_elevation(gmaps, latest_point)
        if rs:
            current_altitude = rs[0].get('elevation')
        else:
            current_altitude = None

        import pyowm
        owm = pyowm.OWM('b1d3074b48c0a002a27a38ab6bf030e4')
        # Search for current weather in London (UK)
        observation = owm.weather_at_coords(latest_point[0], latest_point[1])
        w = observation.get_weather()
        weather = {
            'wind': w.get_wind(),  # {'speed': 4.6, 'deg': 330}
            'humidity': w.get_humidity(), # 87
            'temprature': w.get_temperature('celsius'),  # {'temp_max': 10.5, 'temp': 9.7, 'temp_min': 9.0}
        }

        result = {
            'id': track.id,
            'terrain': terrain,
            'advices': advices,
            'latest_point': latest_point,
            'prev_point': prev_point,
            'inserctions': inserctions,
            'altitude': current_altitude,
            'weather': weather,
            'speed': speed,
            'angle': angle,
        }

        return result


class AuthApiView(JSONView):
    def get_data(self, **response_kwargs):
        token = Token()
        token.save()
        return token.dict()


def calculate_initial_compass_bearing(pointA, pointB):
    """
    Calculates the bearing between two points.
    The formulae used is the following:
        θ = atan2(sin(Δlong).cos(lat2),
                  cos(lat1).sin(lat2) − sin(lat1).cos(lat2).cos(Δlong))
    :Parameters:
      - `pointA: The tuple representing the latitude/longitude for the
        first point. Latitude and longitude must be in decimal degrees
      - `pointB: The tuple representing the latitude/longitude for the
        second point. Latitude and longitude must be in decimal degrees
    :Returns:
      The bearing in degrees
    :Returns Type:
      float
    """
    if (type(pointA) != tuple) or (type(pointB) != tuple):
        raise TypeError("Only tuples are supported as arguments")

    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
            * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2 return values
    # from -180° to + 180° which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing


def get_elevation(gmaps, point):
    m = hashlib.md5()
    m.update(str(point))
    key = m.hexdigest()

    c = cache.get(key)
    if c:
        logging.warning("Use cache")
        return c
    else:
        r = elevation.elevation(gmaps, point)
        cache.set(key, r)
        return r


def get_elevation_path(gmaps, points, METERS_LOOK):

    m = hashlib.md5()
    for p in points:
        m.update(str(p))
    m.update(str(METERS_LOOK))

    key = m.hexdigest()

    c = cache.get(key)
    if c:
        logging.warning("Use cache")
        return c
    else:
        r = elevation.elevation_along_path(gmaps, points, METERS_LOOK)
        cache.set(key, r)
        return r