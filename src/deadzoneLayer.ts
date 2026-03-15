/**
 * Custom Leaflet canvas layer that renders deadzone regions as white stippled/dotted circles.
 * Dot opacity scales from ~30% to ~80% based on the region's priority score.
 */

import L from "leaflet";
import { type DeadzoneRegion } from "./types.ts";

const MIN_DOT_RADIUS = 1.5;
const MAX_DOT_RADIUS = 3.5;
const MIN_DOT_SPACING = 7;
const MAX_DOT_SPACING = 14;
const MIN_OPACITY = 0.3;
const MAX_OPACITY = 0.8;

/**
 * Compute the circle radius in pixels for a given region area at the current zoom level.
 * Treats the region as a circle with equivalent area and converts its geographic radius to pixels.
 */
function regionRadiusPx(map: L.Map, region: DeadzoneRegion): number {
  const radiusKm = Math.sqrt(region.area_km2 / Math.PI);
  const radiusMeters = radiusKm * 1000;
  const center = L.latLng(region.center_lat, region.center_lon);
  const edgePoint = center.toBounds(radiusMeters * 2);
  const centerPx = map.latLngToContainerPoint(center);
  const edgePx = map.latLngToContainerPoint(L.latLng(edgePoint.getNorth(), center.lng));
  return Math.max(Math.abs(centerPx.y - edgePx.y), 8);
}

class DeadzoneCanvasLayer extends L.Layer {
  private _canvas: HTMLCanvasElement | null = null;
  private _regions: DeadzoneRegion[] = [];
  private _map: L.Map | null = null;

  constructor(regions: DeadzoneRegion[]) {
    super();
    this._regions = regions;
  }

  onAdd(map: L.Map): this {
    this._map = map;
    this._canvas = L.DomUtil.create("canvas", "deadzone-canvas-layer") as HTMLCanvasElement;
    const pane = map.getPane("overlayPane");
    if (pane) {
      pane.appendChild(this._canvas);
    }
    this._canvas.style.position = "absolute";
    this._canvas.style.pointerEvents = "none";

    map.on("moveend zoomend resize", this._redraw, this);
    this._redraw();
    return this;
  }

  onRemove(map: L.Map): this {
    if (this._canvas && this._canvas.parentNode) {
      this._canvas.parentNode.removeChild(this._canvas);
    }
    map.off("moveend zoomend resize", this._redraw, this);
    this._canvas = null;
    this._map = null;
    return this;
  }

  updateRegions(regions: DeadzoneRegion[]): void {
    this._regions = regions;
    this._redraw();
  }

  private _redraw(): void {
    if (!this._map || !this._canvas) return;

    const map = this._map;
    const size = map.getSize();
    const canvas = this._canvas;

    canvas.width = size.x;
    canvas.height = size.y;

    // Position canvas at the top-left of the map container
    const topLeft = map.containerPointToLayerPoint(L.point(0, 0));
    L.DomUtil.setPosition(canvas, topLeft);

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (const region of this._regions) {
      this._drawRegionStipple(ctx, map, region);
    }
  }

  private _drawRegionStipple(ctx: CanvasRenderingContext2D, map: L.Map, region: DeadzoneRegion): void {
    const center = map.latLngToContainerPoint(L.latLng(region.center_lat, region.center_lon));
    const radius = regionRadiusPx(map, region);
    const score = region.priority_score;
    const opacity = MIN_OPACITY + (MAX_OPACITY - MIN_OPACITY) * score;

    // Scale dot size and density with severity — worst deadzones get bigger, denser dots
    const dotRadius = MIN_DOT_RADIUS + (MAX_DOT_RADIUS - MIN_DOT_RADIUS) * score;
    const dotSpacing = MAX_DOT_SPACING - (MAX_DOT_SPACING - MIN_DOT_SPACING) * score;

    ctx.save();
    ctx.globalAlpha = opacity;
    ctx.fillStyle = "white";

    const startX = center.x - radius;
    const startY = center.y - radius;
    const endX = center.x + radius;
    const endY = center.y + radius;

    for (let x = startX; x <= endX; x += dotSpacing) {
      for (let y = startY; y <= endY; y += dotSpacing) {
        const dx = x - center.x;
        const dy = y - center.y;
        if (dx * dx + dy * dy <= radius * radius) {
          ctx.beginPath();
          ctx.arc(x, y, dotRadius, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    ctx.restore();
  }
}

export { DeadzoneCanvasLayer };
