ymaps.ready(init);

function init() {
    const addressInput = document.getElementById("id_address");
    const latitudeInput = document.getElementById("id_latitude");
    const longitudeInput = document.getElementById("id_longitude");
    const initialAddressNode = document.getElementById("initial-event-address");
    const initialLatitudeNode = document.getElementById("initial-event-latitude");
    const initialLongitudeNode = document.getElementById("initial-event-longitude");

    const initialAddress = initialAddressNode ? JSON.parse(initialAddressNode.textContent) : "";
    const initialLatitude = initialLatitudeNode ? JSON.parse(initialLatitudeNode.textContent) : "";
    const initialLongitude = initialLongitudeNode ? JSON.parse(initialLongitudeNode.textContent) : "";

    let myPlacemark = null;
    const myMap = new ymaps.Map(
        "map",
        {
            center: [55.753994, 37.622093],
            zoom: 12,
        },
        {
            searchControlProvider: "yandex#search",
        }
    );

    myMap.events.add("click", function (e) {
        const coords = e.get("coords");

        if (myPlacemark) {
            myPlacemark.geometry.setCoordinates(coords);
        } else {
            myPlacemark = createPlacemark(coords);
            myMap.geoObjects.add(myPlacemark);
            myPlacemark.events.add("dragend", function () {
                updateAddress(myPlacemark.geometry.getCoordinates());
            });
        }

        updateAddress(coords);
    });

    function createPlacemark(coords) {
        return new ymaps.Placemark(
            coords,
            {
                iconCaption: "Поиск адреса...",
            },
            {
                preset: "islands#redDotIconWithCaption",
                draggable: true,
            }
        );
    }

    function updateAddress(coords) {
        if (latitudeInput) {
            latitudeInput.value = coords[0];
        }
        if (longitudeInput) {
            longitudeInput.value = coords[1];
        }

        myPlacemark.properties.set("iconCaption", "Поиск адреса...");
        ymaps.geocode(coords).then(function (res) {
            const firstGeoObject = res.geoObjects.get(0);
            if (!firstGeoObject) {
                return;
            }

            const addressLine = firstGeoObject.getAddressLine();
            if (addressInput) {
                addressInput.value = addressLine;
            }

            myPlacemark.properties.set({
                iconCaption: addressLine,
                balloonContent: addressLine,
            });
        });
    }

    if (initialLatitude && initialLongitude) {
        const coords = [Number(initialLatitude), Number(initialLongitude)];
        myPlacemark = createPlacemark(coords);
        myMap.geoObjects.add(myPlacemark);
        myMap.setCenter(coords, 14);

        if (addressInput && initialAddress) {
            addressInput.value = initialAddress;
        }
        if (latitudeInput) {
            latitudeInput.value = initialLatitude;
        }
        if (longitudeInput) {
            longitudeInput.value = initialLongitude;
        }

        updateAddress(coords);
    }
}
