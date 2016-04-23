# -*- coding: utf-8 -*-

# common
import math

# django
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.conf import settings

# other
import googlemaps
from googlemaps import elevation

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


class CreateTrackApiView(JSONView):
    def get_data(self, **response_kwargs):
        track = Track()
        track.save()
        return track.dict()


class UpadateTrackApiView(JSONView):
    def get_data(self, track_id):
        track = get_object_or_404(Track, id=track_id)
        lat = float(self.REQUEST.get('lat'))
        long = float(self.REQUEST.get('long'))
        alt = float(self.REQUEST.get('alt'))
        METERS_LOOK = int(self.REQUEST.get('look_ahead', 100))
        assert lat and long and alt

        point = {
            'lat': lat,
            'lng': long,
            'alt': alt,
        }

        if not track.points:
            track.points = []
        track.points.append(point)
        track.save()

        gmaps = googlemaps.Client(key=settings.MAPS_GOOGLE_KEY)

        latest_point = track.get_point(0)
        prev_point = None
        if latest_point:
            current_index = 1
            while True:
                prev_point = track.get_point(current_index)
                if not prev_point:
                    break

                if vincenty(prev_point, latest_point).miles > 0.01:
                    break

                current_index += 1


        advices = []
        terrain = {
            'highest_point': None,
            'distance_to_highest_point': None,
        }
        if latest_point and prev_point:
            terrain['highest_point'] = 0
            terrain['distance_to_highest_point'] = 0

            bearing = calculate_initial_compass_bearing(prev_point, latest_point)


            origin = geopy.Point(latest_point[0], latest_point[1])
            destination = VincentyDistance(meters=METERS_LOOK).destination(origin, bearing)

            point100 = destination.latitude, destination.longitude

            rs = elevation.elevation_along_path(gmaps, [latest_point, point100], METERS_LOOK)

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

        result = {
            'id': track.id,
            'terrain': terrain,
            'advices': advices,
            'latest_point': latest_point,
            'prev_point': prev_point,
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
