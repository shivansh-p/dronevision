$(function() {
  var map, marker, radius;

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

  $('#radius').on('input', function() {
    setParams(getCurrentParams());
  });

  $('#lat, #lng').on('change', function() {
    var currentParams = getCurrentParams();

    moveTo(currentParams.lat, currentParams.lng);
  });

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
      lng: $('#lng').val()
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

  initMap();
  setParams(getCurrentParams());

  var stepInterval;
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

  var trackId;
  function track(params) {
    if (!trackId) {
      $.ajax({
        url: '/api/track',
        method: 'POST',
        dataType: 'json'
      }).done(function (response) {
        trackId = response.id;
      });
    } else {
       $.ajax({
        url: '/api/track/' + trackId,
        method: 'POST',
        dataType: 'json',
        data: params
      });
    }
  }
});