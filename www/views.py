# django
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

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


class CreateTrackApiView(JSONView):
    def get_data(self, **response_kwargs):
        track = Track()
        track.save()
        return track.dict()


class UpadateTrackApiView(JSONView):
    def get_data(self, track_id):
        track = get_object_or_404(Track, id=track_id)
        lat = self.REQUEST.get('lat')
        long = self.REQUEST.get('long')
        alt = self.REQUEST.get('alt')
        assert lat and long and alt

        point = {
            'lat': lat,
            'long': long,
            'alt': alt,
        }

        if not track.points:
            track.points = []
        track.points.append(point)
        track.save()

        return track.dict()


class AuthApiView(JSONView):
    def get_data(self, **response_kwargs):
        token = Token()
        token.save()
        return token.dict()