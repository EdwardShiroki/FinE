const address = JSON.parse(document.getElementById("alfa").textContent);
const latitudeNode = document.getElementById("event-latitude");
const longitudeNode = document.getElementById("event-longitude");
const latitude = latitudeNode ? JSON.parse(latitudeNode.textContent) : "";
const longitude = longitudeNode ? JSON.parse(longitudeNode.textContent) : "";

ymaps.ready(init);

function init() {
    const myMap = new ymaps.Map("map", {
        center: [55.753994, 37.622093],
        zoom: 9,
    });

    if (latitude && longitude) {
        const coords = [Number(latitude), Number(longitude)];
        const placemark = new ymaps.Placemark(coords, {
            balloonContent: address,
            iconCaption: address,
        });
        myMap.geoObjects.add(placemark);
        myMap.setCenter(coords, 14);
        return;
    }

    ymaps.geocode(address, { results: 1 }).then(function (res) {
        const firstGeoObject = res.geoObjects.get(0);
        if (!firstGeoObject) {
            return;
        }

        const bounds = firstGeoObject.properties.get("boundedBy");
        myMap.geoObjects.add(firstGeoObject);
        myMap.setBounds(bounds, {
            checkZoomRange: true,
        });
    });
}
