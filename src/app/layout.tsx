import type { Metadata } from "next";
import Script from "next/script";
import { getSession } from "@/lib/auth/session";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import FlashMessages from "@/components/layout/FlashMessages";
import type { FlashMessage } from "@/types";

export const metadata: Metadata = {
  title: "Analysis Facility",
  description: "ATLAS Analysis Facility at UChicago",
  icons: { icon: "/img/atlas-favicon.ico" },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getSession();
  let flash: FlashMessage | undefined;
  if (session.flash) {
    flash = session.flash;
    session.flash = undefined;
    await session.save();
  }

  return (
    <html lang="en">
      <head>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
          integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
          crossOrigin="anonymous"
        />
        <link
          rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css"
          integrity="sha512-Kc323vGBEqzTmouAECnVceyQqyqdsSiqLQISBL29aUW4U/M7pSPA/gEUZQqv1cwx4OnYxTxve5UMg5GT6L4JJg=="
          crossOrigin="anonymous"
          referrerPolicy="no-referrer"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Open+Sans"
        />
        <link rel="stylesheet" href="/css/style.css" />
      </head>
      <body>
        <Navbar
          isAuthenticated={session.is_authenticated ?? false}
          role={session.role}
        />
        <div id="messages">
          {flash && <FlashMessages flash={flash} />}
        </div>
        {children}
        <Footer />
        <Script
          src="https://code.jquery.com/jquery-3.7.1.min.js"
          integrity="sha256-/JqT3SQfawRcv/BIHPThkBvs0OEvtFFmqPF/lYI/Cxo="
          crossOrigin="anonymous"
          strategy="beforeInteractive"
        />
        <Script
          src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
          integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz"
          crossOrigin="anonymous"
          strategy="afterInteractive"
        />
      </body>
    </html>
  );
}
