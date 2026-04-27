import Breadcrumb from "@/components/ui/Breadcrumb";

export const metadata = { title: "Analysis Facility - About" };

export default function About() {
  return (
    <section>
      <div className="container">
        <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "About" }]} />
        <h4 className="text-center fw-lighter mb-4">
          ATLAS Analysis Facility at UChicago
        </h4>
        <p>
          The ATLAS Analysis Facility at UChicago offers users a mix of
          traditional batch computing alongside of forward-looking technologies
          like Kubernetes, Jupyter and Dask. Access is granted to U.S. ATLAS
          physicists and their collaborators, including students and members of
          the international ATLAS Collaboration.
        </p>
      </div>
    </section>
  );
}
