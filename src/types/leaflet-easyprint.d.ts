import "leaflet";

declare module "leaflet" {
  interface EasyPrintOptions {
    title?: string;
    position?: string;
    sizeModes?: string[];
    filename?: string;
    exportOnly?: boolean;
    hidden?: boolean;
  }

  function easyPrint(options: EasyPrintOptions): Control;
}
