import L from "leaflet";

const redPinMarker = L.divIcon({
  html: `
    <ul style="list-style-type: none; padding: 0; margin: 0;">
        <li style="color: red; font-size: 30px;">📍</li>
    </ul>`,
  iconSize: [30, 30],
  iconAnchor: [15, 30],
});

const chirpyMarker = L.divIcon({
  html: `
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="40" viewBox="0 0 24 40">
  <circle cx="12" cy="12" r="10" fill="#4a90d9" stroke="#fff" stroke-width="2"/>
  <polygon points="12,40 4,16 20,16" fill="#4a90d9"/>
</svg>`,
  className: "",
  iconSize: [24, 40],
  iconAnchor: [12, 40],
});
export { chirpyMarker, redPinMarker };
