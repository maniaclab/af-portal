import { getSession } from "@/lib/auth/session";
import Image from "next/image";

export default async function Home() {
  const session = await getSession();
  const isAuthenticated = session.is_authenticated ?? false;

  return (
    <section>
      <div className="container text-center">
        <Image
          id="site-logo"
          src="/img/atlas-af-logo2.png"
          alt="ATLAS Analysis Facility"
          width={400}
          height={200}
          style={{ width: "25%", height: "auto", margin: "2em 0" }}
        />
        <h4>An analysis facility for the ATLAS collaboration</h4>
        <p id="carousel"></p>
        {!isAuthenticated && (
          <>
            <a
              href="/auth/login"
              role="button"
              className="btn btn-sm btn-primary me-2"
            >
              Login
            </a>
            <a
              href="/signup"
              role="button"
              className="btn btn-sm btn-primary"
            >
              Signup
            </a>
          </>
        )}
      </div>
    </section>
  );
}
