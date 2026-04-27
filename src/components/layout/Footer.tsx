import Image from "next/image";

export default function Footer() {
  return (
    <footer className="text-center">
      <a href="https://www.uchicago.edu" target="_blank" rel="noreferrer">
        <Image src="/img/uc-logo.png" alt="UChicago" height={55} width={110} style={{ height: 55, width: "auto" }} />
      </a>
      <a href="https://efi.uchicago.edu" target="_blank" rel="noreferrer">
        <Image
          src="/img/efi-logo.png"
          alt="EFI"
          height={55}
          width={110}
          style={{ height: 55, width: "auto", marginRight: 50 }}
        />
      </a>
      <a href="https://iris-hep.org" target="_blank" rel="noreferrer">
        <Image
          src="/img/iris-hep-logo.png"
          alt="IRIS-HEP"
          height={55}
          width={110}
          style={{ height: 55, width: "auto" }}
        />
      </a>
    </footer>
  );
}
