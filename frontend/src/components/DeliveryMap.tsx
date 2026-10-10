import { useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
const places = [
  {
    name: "Демо: Бишкек, проспект Чуй, 100",
    point: [42.875, 74.609] as [number, number],
  },
  {
    name: "Демо: Бишкек, улица Киевская, 80",
    point: [42.87, 74.597] as [number, number],
  },
  {
    name: "Демо: Бишкек, улица Токтогула, 120",
    point: [42.868, 74.605] as [number, number],
  },
];
export default function DeliveryMap({
  onSelect,
}: {
  onSelect: (address: string) => void;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <div className="delivery-map">
      <p className="muted">
        Учебные точки в Бишкеке. Для заказа уточните адрес, дом и квартиру.
      </p>
      {failed ? (
        <p role="status">
          Карта недоступна. Можно выбрать учебный адрес ниже или ввести свой.
        </p>
      ) : (
        <MapContainer
          center={[42.872, 74.603]}
          zoom={14}
          minZoom={12}
          maxZoom={17}
          scrollWheelZoom={false}
          style={{ height: 280, width: "100%" }}
        >
          <TileLayer
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            eventHandlers={{ tileerror: () => setFailed(true) }}
          />
          {places.map((place) => (
            <CircleMarker
              key={place.name}
              center={place.point}
              radius={10}
              pathOptions={{ color: "#176348", fillOpacity: 0.8 }}
            >
              <Popup>
                {place.name}
                <br />
                <button type="button" onClick={() => onSelect(place.name)}>
                  Выбрать адрес
                </button>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      )}
      <div className="demo-addresses">
        {places.map((place) => (
          <button
            type="button"
            key={place.name}
            onClick={() => onSelect(place.name)}
          >
            {place.name}
          </button>
        ))}
      </div>
      <a
        className="muted"
        href="https://www.openstreetmap.org/fixthemap"
        target="_blank"
        rel="noreferrer"
      >
        Сообщить об ошибке на карте ↗
      </a>
    </div>
  );
}
