declare module "georaster" {
  import { type GeoRaster } from "../types";
  export default function parseGeoraster(data: ArrayBuffer | string): Promise<GeoRaster>;
}
