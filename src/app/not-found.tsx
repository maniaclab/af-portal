export default function NotFound() {
  return (
    <section>
      <div className="container text-center">
        <h1 className="display-6 my-4">404 Not Found</h1>
        <p>The page you requested was not found.</p>
        <p>
          Click{" "}
          <a href="/" className="text-decoration-none">
            here
          </a>{" "}
          to go to the home page.
        </p>
      </div>
    </section>
  );
}
