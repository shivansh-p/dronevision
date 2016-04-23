# django imports
from django.conf.urls import url

# my imports
from views import HomeView, CreateTrackApiView, AuthApiView, UpadateTrackApiView


urlpatterns = [
    url(r'^$', HomeView.as_view()),
    url(r'^api/auth', AuthApiView.as_view()),
    url(r'^api/track$', CreateTrackApiView.as_view()),
    url(r'^api/track/(?P<track_id>[0-9]+)$', UpadateTrackApiView.as_view()),
]
