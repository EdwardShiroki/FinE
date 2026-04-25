(function () {
    function parseEvents() {
        const source = document.getElementById("events-map-data");
        if (!source) {
            return [];
        }

        try {
            const parsed = JSON.parse(source.textContent || "[]");
            return parsed.filter((event) =>
                Number.isFinite(event.latitude) && Number.isFinite(event.longitude)
            );
        } catch (error) {
            return [];
        }
    }

    function haversineDistance(first, second) {
        const toRadians = (value) => (value * Math.PI) / 180;
        const earthRadiusKm = 6371;
        const deltaLatitude = toRadians(second.latitude - first.latitude);
        const deltaLongitude = toRadians(second.longitude - first.longitude);
        const firstLatitude = toRadians(first.latitude);
        const secondLatitude = toRadians(second.latitude);

        const a =
            Math.sin(deltaLatitude / 2) ** 2 +
            Math.cos(firstLatitude) *
                Math.cos(secondLatitude) *
                Math.sin(deltaLongitude / 2) ** 2;

        return earthRadiusKm * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    function renderList(events, focusEvent) {
        const list = document.getElementById("nearby-events-list");
        if (!list) {
            return;
        }

        if (events.length === 0) {
            list.innerHTML = '<div class="nearby-events-item"><strong>Нет событий с координатами</strong><span>Добавьте широту и долготу при создании мероприятия.</span></div>';
            return;
        }

        list.innerHTML = "";
        events.forEach((event) => {
            const card = document.createElement("button");
            card.type = "button";
            card.className = "nearby-events-item";
            card.innerHTML = [
                `<strong>${event.name}</strong>`,
                `<span>${event.address || "Адрес не указан"}</span>`,
                event.distance_km != null
                    ? `<span>Около ${event.distance_km.toFixed(1)} км</span>`
                    : `<span>${event.start_day} - ${event.finish_day}</span>`,
            ].join("");
            card.addEventListener("click", function () {
                focusEvent(event);
            });
            list.appendChild(card);
        });
    }

    function updateStatus(message) {
        const status = document.getElementById("nearby-events-status");
        if (status) {
            status.textContent = message;
        }
    }

    function initMap() {
        const events = parseEvents();
        const mapNode = document.getElementById("nearby-events-map");
        if (!mapNode) {
            return;
        }

        if (!window.ymaps) {
            updateStatus("Карта недоступна: Yandex Maps API не загрузился.");
            renderList(events, function () {});
            return;
        }

        if (events.length === 0) {
            updateStatus("Нет мероприятий с заполненными координатами.");
            renderList([], function () {});
            return;
        }

        window.ymaps.ready(function () {
            const firstEvent = events[0];
            const map = new window.ymaps.Map("nearby-events-map", {
                center: [firstEvent.latitude, firstEvent.longitude],
                zoom: 10,
                controls: ["zoomControl", "fullscreenControl"],
            });

            const bounds = [];
            const placemarks = new Map();

            events.forEach((event) => {
                const coordinates = [event.latitude, event.longitude];
                bounds.push(coordinates);
                const placemark = new window.ymaps.Placemark(
                    coordinates,
                    {
                        balloonContentHeader: event.name,
                        balloonContentBody: event.address || "Адрес не указан",
                        balloonContentFooter: `${event.start_day} - ${event.finish_day}`,
                    },
                    {
                        preset: "islands#blueIcon",
                    }
                );
                map.geoObjects.add(placemark);
                placemarks.set(event.id, placemark);
            });

            if (bounds.length > 1) {
                map.setBounds(bounds, {
                    checkZoomRange: true,
                    zoomMargin: 24,
                });
            }

            function focusEvent(event) {
                const placemark = placemarks.get(event.id);
                map.setCenter([event.latitude, event.longitude], 13, {
                    duration: 200,
                });
                if (placemark) {
                    placemark.balloon.open();
                }
            }

            renderList(events.slice(0, 5), focusEvent);
            updateStatus("Показываю мероприятия с указанными координатами.");

            if (!navigator.geolocation) {
                return;
            }

            navigator.geolocation.getCurrentPosition(
                function (position) {
                    const currentLocation = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                    };

                    const geoPlacemark = new window.ymaps.Placemark(
                        [currentLocation.latitude, currentLocation.longitude],
                        {
                            balloonContentHeader: "Вы здесь",
                        },
                        {
                            preset: "islands#redCircleDotIcon",
                        }
                    );
                    map.geoObjects.add(geoPlacemark);

                    const nearestEvents = events
                        .map((event) => ({
                            ...event,
                            distance_km: haversineDistance(currentLocation, event),
                        }))
                        .sort((left, right) => left.distance_km - right.distance_km)
                        .slice(0, 5);

                    renderList(nearestEvents, focusEvent);
                    updateStatus("Показываю ближайшие события относительно вашей геопозиции.");
                },
                function () {
                    updateStatus("Геопозиция недоступна, показываю все события с координатами.");
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000,
                }
            );
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initMap);
    } else {
        initMap();
    }
})();
