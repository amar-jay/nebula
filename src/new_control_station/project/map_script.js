// Rotated Marker Function
(function() {
    // save these original methods before they are overwritten
    var proto_initIcon = L.Marker.prototype._initIcon;
    var proto_setPos = L.Marker.prototype._setPos;

    var oldIE = (L.DomUtil.TRANSFORM === 'msTransform');

    L.Marker.addInitHook(function () {
        var iconOptions = this.options.icon && this.options.icon.options;
        var iconAnchor = iconOptions && this.options.icon.options.iconAnchor;
        if (iconAnchor) {
            iconAnchor = (iconAnchor[0] + 'px ' + iconAnchor[1] + 'px');
        }
        this.options.rotationOrigin = this.options.rotationOrigin || iconAnchor || 'center bottom' ;
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
            if(this.options.rotationAngle) {
                this._icon.style[L.DomUtil.TRANSFORM+'Origin'] = this.options.rotationOrigin;

                if(oldIE) {
                    // for IE 9, use the 2D rotation
                    this._icon.style[L.DomUtil.TRANSFORM] = 'rotate(' + this.options.rotationAngle + 'deg)';
                } else {
                    // for modern browsers, prefer the 3D accelerated version
                    this._icon.style[L.DomUtil.TRANSFORM] += ' rotateZ(' + this.options.rotationAngle + 'deg)';
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
// Rotated Marker part is taken from this repo: https://github.com/bbecquet/Leaflet.RotatedMarker
// Huge thanks to its contributors

// Take the generated map variable from folium
var map = %s;


var uavIcon = L.icon({
    iconUrl: 'data:image/png;base64,%s', 
    iconSize: [40, 40],
    });
    
var targetIcon = L.icon({
    iconUrl: 'data:image/png;base64,%s', 
    iconSize: [40, 40],
    });
    
var userIcon = L.icon({
    iconUrl: 'data:image/png;base64,%s', 
    iconSize: [40, 40],
    });

var homeIcon = L.icon({
    iconUrl: 'data:image/png;base64,%s', 
    iconSize: [40, 40],
    });
    

var intial_location = [41.27442, 28.727317]
var inp_initial_location = "%s".split(",").map(Number)

if (isNaN(inp_initial_location[0]) || isNaN(inp_initial_location[1])){
	console.error("Initial location is not valid, using Istanbul Airport as default")
} else {
	intial_location = inp_initial_location
}


// Adding First Marker
var mymarker = L.marker(
	intial_location,
        {}
    ).addTo(map);

// Some Functions To Make Map Interactive
function moveMarkerByClick(e) {
    console.log(e.latlng.lat + "," +e.latlng.lng);
    mymarker.setLatLng([e.latlng.lat, e.latlng.lng])
}

function undoWaypoint() {
    if(waypoints.length >0)
        waypoints.pop().remove();
    if(lines.length > 0)
        lines.pop().remove();
}

// To plan a mission putting waypoints to the places that we want uav to go
var waypointNumber = 0;
var waypoints = [];
var lines = [];
function putWaypointEvent(e) {
    putWaypoint(e.latlng.lat, e.latlng.lng)
}

function putWaypoint(lat, lng) {
    var marker = L.marker(
        [lat, lng],
        {}
    ).addTo(map);
    
    // Add lines between last to waypoints
    if(waypoints.length > 0){
        points = [waypoints[waypoints.length-1].getLatLng(), marker.getLatLng()];
        line = L.polyline(points, {color: 'red'}).addTo(map);
        lines.push(line);
    }
    waypoints.push(marker);
}

var rect = 0;
var corners = 0;
function drawRectangle(e) {
    if (corners.length == 0) {
        corners.push(e.latlng);
    } else if (corners.length == 1){
        corners.push(e.latlng);
        rect = L.rectangle(corners, {color: "#ff7800", weight: 1}).addTo(map);
    } else {
        corners = [];
        corners.push(e.latlng);
        map.removeLayer(rect);
    }
}

function setMission(mission_type) {
    var msg = "m";
    if (mission_type){ // waypoints
        for(let i = 0; i < waypoints.length; i++){
            msg += waypoints[i].getLatLng().lat + "," + waypoints[i].getLatLng().lng ;
            if (i < waypoints.length-1){
                msg += "&"
            }
        }
    }
    else{ // exploration
        for(let i = 0; i < 2; i++){
            msg += corners[i].lat + "," + corners[i].lng;
            if (i < corners.length-1){
                msg += "&"
            }
        }
    }
    console.log(msg);
}

function clearAll() {
    if (waypoints.length > 0){
        for(let i = 0; i < waypoints.length; i++){
            waypoints[i].remove();
        }
        waypoints = [];
    }
    if (lines.length > 0){
        for(let i = 0; i < lines.length; i++){
            lines[i].remove();
        }
        lines = [];
    }
    if (rect != 0){
        map.removeLayer(rect);
    }
}

// Initial mode for clicking on the map
map.on('click', moveMarkerByClick);

// end custom code