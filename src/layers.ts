import L from "leaflet";

const redPinMarker = L.divIcon({
  html: `
    <ul style="list-style-type: none; padding: 0; margin: 0;">
        <li style="color: red; font-size: 30px;">📍</li>
    </ul>`,
  iconSize: [30, 30],
  iconAnchor: [15, 30],
});

export { redPinMarker };
