$(function() {
  var map, marker, radius, stepInterval, trackId;

  function initMap() {
    var currentParams = getCurrentParams();

    map = new google.maps.Map(document.getElementById('map'), {
      zoom: 15,
      mapTypeId: google.maps.MapTypeId.TERRAIN,
      center: {lat: currentParams.lat, lng: currentParams.lng}
    });

    // This event listener will call addMarker() when the map is clicked.
    map.addListener('click', function(event) {
      addDrone(event.latLng);
    });
  }

  function addDrone(location) {
    deleteDrone();
    var currentParams = getCurrentParams();

    marker = new google.maps.Marker({
      position: location,
      map: map,
      title: 'Drone location'
    });

    radius = new google.maps.Circle({
      map: map,
      radius: currentParams.radius,
      fillColor: '#337ab7',
      strokeWeight: 1,
      strokeOpacity: 0.8,
      strokeColor: '#337ab7'
    });

    radius.bindTo('center', marker, 'position');

    var newParams = Object.assign({}, currentParams, {
      lat: location.lat(),
      lng: location.lng()
    });

    setParams(newParams);
  }

  function setMapOnAll(map) {
    if (marker) {
      marker.setMap(map);
      radius.setMap(map);
    }
  }

  function deleteDrone() {
    setMapOnAll(null);
    radius = undefined;
    marker = undefined;
  }

  function setParams(params) {
    for (var field in params) {
      $('#' + field).val(params[field]);
    }

    if (params.radius) {
      $('#current-radius').text(params.radius);

      if (radius) {
        radius.set('radius', params.radius);
      }
    }
  }

  function getCurrentParams() {
    var params = {
      radius: $('#radius').val(),
      alt: $('#alt').val(),
      lat: $('#lat').val(),
      lng: $('#lng').val(),
      look_ahead: $('#look_ahead').val()
    };

    for (var field in params) {
      params[field] = parseFloat(params[field]);
    }

    return params;
  }

  function moveTo(lat, lng) {
    var location = new google.maps.LatLng(lat, lng);

    if (!marker) {
      addDrone(location);
    }

    marker.setPosition(location);
    map.panTo(location);
  }

  function track(params) {
    if (!trackId) {
      $.ajax({
        url: 'http://dontcrashmydrone.ferumflex.com/api/track',
        method: 'POST',
        dataType: 'json'
      }).done(function(response) {
        trackId = response.id;
        track(params);
      });
    } else {
      $.ajax({
        url: 'http://dontcrashmydrone.ferumflex.com/api/track/' + trackId,
        method: 'POST',
        dataType: 'json',
        data: params
      }).done(function(response) {
        if (response) {
          $('#info').show();
        }

        if (response.advices.length) {
          $('.hit-terrain').fadeIn(300);
        } else {
          $('.hit-terrain').hide();
        }

        if (response.speed) {
          $('.info--general-speed').text(Math.round((response.speed * 3.6)) + ' km/h');
        }

        if (response.angle) {
          var deg = response.angle.toFixed(0);
          $('.info--general-dir').text(deg + '°').show();
          $('.info--general-dir-comp').css({
            transform: 'rotate(' + deg + 'deg)'
          }).show();
        } else {
          $('.info--general-dir').hide();
          $('.info--general-dir-comp').hide();
        }

        if (response.terrain.highest_point) {
          $('.info--terrain-highest-point').text(response.terrain.highest_point.toFixed(2));
        }

        if (response.inserctions.total) {
          $('.info--terrain-no-flight-zone').text('YES').closest('tr').removeClass('success').addClass('danger');
          $('.no-flights').fadeIn(300);
        } else {
          $('.info--terrain-no-flight-zone').text('NO').closest('tr').removeClass('danger').addClass('success');
          $('.no-flights').hide();
        }

        if (response.weather.humidity) {
          $('.info--weather-humidity').text(response.weather.humidity + '%');

          if (response.weather.humidity > 80) {
            $('.info--weather-humidity').closest('tr').removeClass('success').addClass('warning');
          } else {
            $('.info--weather-humidity').closest('tr').removeClass('warning').addClass('success');
          }
        }

        if (response.weather.wind) {
          $('.info--weather-wind-speed').text(response.weather.wind.speed + 'm/s');

          if (response.weather.wind.speed > 10) {
            $('.info--weather-wind-speed').closest('tr').removeClass('success').addClass('danger');
          } else {
            $('.info--weather-wind-speed').closest('tr').removeClass('danger').addClass('success');
          }

          if (response.weather.wind.deg) {
            var deg = response.weather.wind.deg.toFixed(0);
            $('.info--weather-wind-dir').text(',' + deg + '°').show();
            $('.info--weather-wind-dir-comp').css({
              transform: 'rotate(' + deg + 'deg)'
            }).show();
          } else {
            $('.info--weather-wind-dir').hide();
            $('.info--weather-wind-dir-comp').hide();
          }
        }

        if (response.weather.temprature) {
          $('.info--weather-temperature').text(response.weather.temprature.temp);
        }
      });
    }
  }

  initMap();
  setParams(getCurrentParams());

  $('#radius').on('input', function() {
    setParams(getCurrentParams());
  });

  $('#lat, #lng').on('change', function() {
    var currentParams = getCurrentParams();

    moveTo(currentParams.lat, currentParams.lng);
  });

  $('#drone-emulation').on('click', function(e) {
    e.preventDefault();
    clearInterval(stepInterval);

    var stepIndex = 0;

    stepInterval = setInterval(function() {
      var point = TEST_DATA[stepIndex];

      if (stepIndex === TEST_DATA.length - 1) {
        clearInterval(stepInterval);
      }

      setParams(point);
      moveTo(point.lat, point.lng);

      var newParams = Object.assign({}, getCurrentParams(), {
        lat: point.lat,
        lng: point.lng
      });

      track(newParams);

      stepIndex++;
    }, 1000);
  });

  $('#get-info').on('click', function(e) {
    e.preventDefault();
    track(getCurrentParams());
  });
});