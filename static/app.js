(function () {
  var map = L.map("map").setView([46.2, 5.2], 10);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map);

  var geoLayer = null;
  var layerMap = {};
  var selectedIdu = null;

  var defaultStyle = { color: "#2563eb", weight: 2, fillOpacity: 0.15 };
  var highlightStyle = { color: "#f59e0b", weight: 3, fillOpacity: 0.4 };

  function clearHighlight() {
    if (!selectedIdu) return;
    var prev = layerMap[selectedIdu];
    if (prev) {
      prev.setStyle(defaultStyle);
    }
    var prevItem = document.querySelector('[data-idu="' + CSS.escape(selectedIdu) + '"]');
    if (prevItem) prevItem.classList.remove("selected");
    selectedIdu = null;
  }

  function highlightParcel(idu, doFly) {
    clearHighlight();
    var layer = layerMap[idu];
    if (!layer) {
      console.warn("highlightParcel: no layer found for", idu);
      return;
    }
    layer.setStyle(highlightStyle);
    if (layer.bringToFront) layer.bringToFront();
    if (doFly !== false) {
      map.flyToBounds(layer.getBounds(), { padding: [50, 50] });
    }
    var item = document.querySelector('[data-idu="' + CSS.escape(idu) + '"]');
    if (item) {
      item.classList.add("selected");
      item.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    selectedIdu = idu;
  }

  function updateMap(geojson) {
    clearHighlight();
    layerMap = {};
    if (geoLayer) {
      map.removeLayer(geoLayer);
    }
    var data = typeof geojson === "string" ? JSON.parse(geojson) : geojson;
    geoLayer = L.geoJSON(data, {
      style: defaultStyle,
      onEachFeature: function (feature, layer) {
        var p = feature.properties;
        layerMap[p.idu] = layer;
        layer.bindPopup(
          "<b>" + (p.adresse || "Adresse inconnue") + "</b><br>" +
          "Surface: " + p.contenance + " m²<br>" +
          "IDU: " + p.idu
        );
        layer.on("click", function () {
          highlightParcel(p.idu, false);
        });
      },
    }).addTo(map);
    if (data.features && data.features.length > 0) {
      map.fitBounds(geoLayer.getBounds(), { padding: [30, 30] });
    }
  }

  document.body.addEventListener("change", function (evt) {
    var radio = evt.target.closest("input[name=surface_mode]");
    if (!radio) return;
    var isExact = radio.value === "exact";
    var exactDiv = document.getElementById("surface-exact");
    var rangeDiv = document.getElementById("surface-range");
    var exactInput = exactDiv.querySelector("input");
    var minInput = rangeDiv.querySelector("input[name=surface_min]");
    var maxInput = rangeDiv.querySelector("input[name=surface_max]");
    if (isExact) {
      exactDiv.style.display = "block";
      rangeDiv.style.display = "none";
      exactInput.required = true;
      minInput.required = false;
      maxInput.required = false;
    } else {
      exactDiv.style.display = "none";
      rangeDiv.style.display = "block";
      exactInput.required = false;
      minInput.required = true;
      maxInput.required = true;
    }
  });

  document.body.addEventListener("click", function (evt) {
    var item = evt.target.closest(".result-item");
    if (!item) return;
    var idu = item.getAttribute("data-idu");
    if (!idu) return;
    evt.preventDefault();
    if (idu === selectedIdu) {
      clearHighlight();
    } else {
      highlightParcel(idu, true);
    }
  });

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
