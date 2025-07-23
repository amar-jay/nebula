// Rotated Marker Function
(function() {
    // Save original methods before they are overwritten
    const proto_initIcon = L.Marker.prototype._initIcon;
    const proto_setPos = L.Marker.prototype._setPos;

    const oldIE = (L.DomUtil.TRANSFORM === 'msTransform');

    L.Marker.addInitHook(function () {
        const iconOptions = this.options.icon && this.options.icon.options;
        let iconAnchor = iconOptions && iconOptions.iconAnchor;
        if (iconAnchor) {
            iconAnchor = iconAnchor[0] + 'px ' + iconAnchor[1] + 'px';
        }
        this.options.rotationOrigin = this.options.rotationOrigin || iconAnchor || 'center bottom';
        this.options.rotationAngle = this.options.rotationAngle || 0;

        // Ensure marker keeps rotated during dragging
        this.on('drag', function(e) { e.target._applyRotation(); });
    });

    L.Marker.include({
        _initIcon: function() {
            proto_initIcon.call(this);
        },

        _setPos: function (pos) {
            proto_setPos.call(this, pos);
            this._applyRotation();
        },

        _applyRotation: function () {
            if (this.options.rotationAngle) {
                this._icon.style[L.DomUtil.TRANSFORM + 'Origin'] = this.options.rotationOrigin;

                if (oldIE) {
                    // for IE 9, use the 2D rotation
                    this._icon.style[L.DomUtil.TRANSFORM] = 'rotate(' + this.options.rotationAngle + 'deg)';
                } else {
                    // for modern browsers, prefer the 3D accelerated version
                    this._icon.style[L.DomUtil.TRANSFORM] = 
                        (this._icon.style[L.DomUtil.TRANSFORM] || '') + 
                        ' rotateZ(' + this.options.rotationAngle + 'deg)';
                }
            }
        },

        setRotationAngle: function(angle) {
            this.options.rotationAngle = angle;
            this.update();
            return this;
        },

        setRotationOrigin: function(origin) {
            this.options.rotationOrigin = origin;
            this.update();
            return this;
        }
    });
})();

// Take the generated map variable from folium
var map = %s;

const droneIcon = L.icon({
    iconUrl: 'data:image/png;base64,%s', 
    iconSize: [40, 40],
});

const targetIcon = L.icon({
    iconUrl: 'data:image/png;base64,%s', 
    iconSize: [40, 40],
});

const userIcon = L.icon({
    iconUrl: 'data:image/png;base64,%s', 
    iconSize: [40, 40],
});

const kamikazeIcon = L.icon({
    iconUrl: 'data:image/png;base64,%s', 
    iconSize: [40, 40],
});

const homeIcon = L.icon({
    iconUrl: 'data:image/png;base64,%s', 
    iconSize: [40, 40],
});

let intial_location = [41.27442, 28.727317];
let inp_initial_location = "%s".split(",").map(Number);

if (isNaN(inp_initial_location[0]) || isNaN(inp_initial_location[1])) {
    console.error("Initial location is not valid, using Istanbul Airport as default");
} else {
    intial_location = inp_initial_location;
}

// Marker Handles
let pos_marker;
let uav_marker;
let target_marker;
let kamikaze_marker;

function moveMarkerByClick(e) {
    console.log("p", e.latlng.lat + "," + e.latlng.lng);
    if (pos_marker) {
        pos_marker.setLatLng(e.latlng);
    } else {
        pos_marker = L.marker([e.latlng.lat, e.latlng.lng]).addTo(map);
    }
}

function updateUavMarker(loc) {
    map.flyTo(loc);
    if (uav_marker) {
        uav_marker.setLatLng({ lat: loc[0], lng: loc[1] });
    } else {
        uav_marker = L.marker(loc, {
            icon: droneIcon,
        }).addTo(map);
    }
}

function updateTargetMarker(loc) {
    map.flyTo(loc);
    if (target_marker) {
        target_marker.setLatLng({ lat: loc[0], lng: loc[1] });
    } else {
        target_marker = L.marker(loc, {
            icon: targetIcon,
        }).addTo(map);
    }
}

function updateKamikazeMarker(loc) {
    map.flyTo(loc);
    if (kamikaze_marker) {
        kamikaze_marker.setLatLng({ lat: loc[0], lng: loc[1] });
    } else {
        kamikaze_marker = L.marker(loc, {
            icon: kamikazeIcon,
        }).addTo(map);
    }
}

function undoWaypoint() {
    if (waypoints.length > 0)
        waypoints.pop().remove();
    if (lines.length > 0)
        lines.pop().remove();
}

// Mission Planning
let waypointNumber = 0;
let waypoints = [];
let lines = [];

function putWaypointEvent(e) {
    putWaypoint(e.latlng.lat, e.latlng.lng);
}


function putWaypoint(lat, lng) {
    const marker = L.marker([lat, lng], {}).addTo(map);

    // Add lines between waypoints
    if (waypoints.length > 0) {
        const points = [waypoints[waypoints.length - 1].getLatLng(), marker.getLatLng()];
        const line = L.polyline(points, { color: 'red' }).addTo(map);
        lines.push(line);
    }
    waypoints.push(marker);
}

// Rectangle Drawing
let rect = null;
let corners = [];

function drawRectangle(e) {
    if (corners.length === 0) {
        corners.push(e.latlng);
    } else if (corners.length === 1) {
        corners.push(e.latlng);
        rect = L.rectangle(corners, { color: "#00aaff", weight: 1 }).addTo(map);
    } else {
        corners = [e.latlng];
        if (rect) map.removeLayer(rect);
        rect = null;
    }
}

// Mission Message Generation
function setMission(mission_type) {
    let msg = "m";
    if (mission_type) {
        // waypoints
        for (let i = 0; i < waypoints.length; i++) {
            const pos = waypoints[i].getLatLng();
            msg += pos.lat + "," + pos.lng;
            if (i < waypoints.length - 1) msg += "&";
        }
    } else {
        // rectangle
        for (let i = 0; i < corners.length && i < 2; i++) {
            msg += corners[i].lat + "," + corners[i].lng;
            if (i < corners.length - 1) msg += "&";
        }
    }
    console.log(msg);
}

// Clean Everything
function clearAll() {
    waypoints.forEach(m => m.remove());
    waypoints = [];

    lines.forEach(l => l.remove());
    lines = [];

    if (rect) {
        map.removeLayer(rect);
        rect = null;
    }

    if (pos_marker) {
        pos_marker.remove();
        pos_marker = null;
    }
}

// Initial click mode
// map.on('click', moveMarkerByClick);

// End custom code

function loadMission(waypoints_str) {
    const waypoint_list = waypoints_str.split("|");

    for (let i = 0; i < waypoint_list.length; i++) {
        if (waypoint_list[i] !== "") {
            const [lat, lng] = waypoint_list[i].split(",").map(Number);
            const marker = L.marker([lat, lng], {}).addTo(map);
            console.log(`Loaded waypoint: ${lat}, ${lng}`);

				    // Add lines between waypoints
				    if (waypoints.length > 0) {
				        const points = [waypoints[waypoints.length - 1].getLatLng(), marker.getLatLng()];
				        const line = L.polyline(points, { color: 'red' }).addTo(map);
				        lines.push(line);
				    }
				    waypoints.push(marker);
        }
    }
}