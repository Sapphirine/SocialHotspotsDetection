//var map;
//function initMap() {
//    var nyc = new google.maps.LatLng(-73.5, 40.5);
//    var map = new google.maps.Map(document.getElementById('map'), {
//      zoom: 13,
//      center: nyc
//    });
////  var heatmap = new google.maps.visualization.HeatmapLayer({
////      data: heatmapData
////  });
////  heatmap.setMap(map);
//}

var map;
function initMap() {
map = new google.maps.Map(document.getElementById('map'), {
  center: {lat: -34.397, lng: 150.644},
  zoom: 8
});
}