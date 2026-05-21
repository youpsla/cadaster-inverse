(function () {
  var map = L.map("map").setView([46.2, 5.2], 10);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map);

  var geoLayer = null;

  function updateMap(geojson) {
    if (geoLayer) {
      map.removeLayer(geoLayer);
    }
    var data = typeof geojson === "string" ? JSON.parse(geojson) : geojson;
    geoLayer = L.geoJSON(data, {
      style: { color: "#2563eb", weight: 2, fillOpacity: 0.15 },
      onEachFeature: function (feature, layer) {
        var p = feature.properties;
        layer.bindPopup(
          "<b>" + (p.adresse || "Adresse inconnue") + "</b><br>" +
          "Surface: " + p.contenance + " m²<br>" +
          "IDU: " + p.idu
        );
      },
    }).addTo(map);
    if (data.features && data.features.length > 0) {
      map.fitBounds(geoLayer.getBounds(), { padding: [30, 30] });
    }
  }

  document.body.addEventListener("htmx:afterSwap", function (evt) {
    if (evt.detail.target.id === "results") {
      var script = document.getElementById("parcels-data");
      if (script) {
        updateMap(script.textContent);
      }
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    var existing = document.getElementById("parcels-data");
    if (existing) {
      updateMap(existing.textContent);
    }
  });
})();
