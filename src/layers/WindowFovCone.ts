import L from "leaflet";

/** Radius of the FOV cone in meters. */
const CONE_RADIUS_M = 500;
/** Number of arc segments for smooth cone rendering. */
const ARC_SEGMENTS = 40;
/** Color of the FOV cone fill and stroke. */
const CONE_COLOR = "#3388ff";

/**
 * Build a lat/lon polygon representing a sector (pie wedge) centered
 * on `center`, spanning `fovDeg` degrees around `azimuthDeg` (CW from north).
 */
export function sectorPoints(
  center: L.LatLng,
  radiusM: number,
  azimuthDeg: number,
  fovDeg: number,
  segments: number,
): L.LatLng[] {
  const halfFov = fovDeg / 2;
  const startAngle = azimuthDeg - halfFov;
  const step = fovDeg / segments;
  const points: L.LatLng[] = [center];
  for (let i = 0; i <= segments; i++) {
    const bearing = startAngle + step * i;
    points.push(destinationPoint(center, radiusM, bearing));
  }
  points.push(center);
  return points;
}

/**
 * Calculate a destination point given a start, distance (m), and bearing (degrees CW from north).
 * Uses spherical earth approximation.
 */
export function destinationPoint(start: L.LatLng, distanceM: number, bearingDeg: number): L.LatLng {
  const R = 6371000; // Earth radius in meters
  const d = distanceM / R;
  const brng = (bearingDeg * Math.PI) / 180;
  const lat1 = (start.lat * Math.PI) / 180;
  const lon1 = (start.lng * Math.PI) / 180;

  const lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(brng));
  const lon2 =
    lon1 + Math.atan2(Math.sin(brng) * Math.sin(d) * Math.cos(lat1), Math.cos(d) - Math.sin(lat1) * Math.sin(lat2));

  return L.latLng((lat2 * 180) / Math.PI, (lon2 * 180) / Math.PI);
}

export interface FovConeHandle {
  /** Update cone geometry from current azimuth/FOV/center. */
  update(center: L.LatLngExpression, azimuthDeg: number, fovDeg: number): void;
  /** Remove cone and drag handle from map. */
  remove(): void;
}

/**
 * Create a FOV cone polygon and a draggable handle marker on the map.
 * Dragging the handle updates the azimuth via the `onAzimuthChange` callback.
 */
export function createFovCone(
  map: L.Map,
  center: L.LatLngExpression,
  azimuthDeg: number,
  fovDeg: number,
  onAzimuthChange: (azimuth: number) => void,
): FovConeHandle {
  const centerLatLng = L.latLng(center);

  // Create the sector polygon
  const points = sectorPoints(centerLatLng, CONE_RADIUS_M, azimuthDeg, fovDeg, ARC_SEGMENTS);
  const polygon = L.polygon(points, {
    color: CONE_COLOR,
    fillColor: CONE_COLOR,
    fillOpacity: 0.15,
    weight: 2,
    interactive: false,
  }).addTo(map);

  // Create a draggable handle at the tip of the cone (center of the arc)
  const handlePos = destinationPoint(centerLatLng, CONE_RADIUS_M, azimuthDeg);
  const handle = L.circleMarker(handlePos, {
    radius: 8,
    color: CONE_COLOR,
    fillColor: "#ffffff",
    fillOpacity: 0.9,
    weight: 2,
    interactive: true,
    bubblingMouseEvents: false,
  }).addTo(map);

  // Make handle draggable via mouse/touch events
  let dragging = false;

  function onMouseMove(e: L.LeafletMouseEvent) {
    if (!dragging) return;
    const dx = e.latlng.lng - centerLatLng.lng;
    const dy = e.latlng.lat - centerLatLng.lat;
    const newAzimuth = ((Math.atan2(dx, dy) * 180) / Math.PI + 360) % 360;
    onAzimuthChange(Math.round(newAzimuth));
  }

  function onMouseUp() {
    dragging = false;
    map.dragging.enable();
    map.off("mousemove", onMouseMove);
    map.off("mouseup", onMouseUp);
  }

  handle.on("mousedown", () => {
    dragging = true;
    map.dragging.disable();
    map.on("mousemove", onMouseMove);
    map.on("mouseup", onMouseUp);
  });

  return {
    update(newCenter: L.LatLngExpression, newAzimuth: number, newFov: number) {
      const c = L.latLng(newCenter);
      const newPoints = sectorPoints(c, CONE_RADIUS_M, newAzimuth, newFov, ARC_SEGMENTS);
      polygon.setLatLngs(newPoints);
      handle.setLatLng(destinationPoint(c, CONE_RADIUS_M, newAzimuth));
    },
    remove() {
      map.removeLayer(polygon);
      map.removeLayer(handle);
      map.off("mousemove", onMouseMove);
      map.off("mouseup", onMouseUp);
    },
  };
}
