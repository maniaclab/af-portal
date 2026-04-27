import QRCode from "qrcode";

export async function generateQRCodeDataURL(text: string): Promise<string> {
  return QRCode.toDataURL(text);
}
