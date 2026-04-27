import Breadcrumb from "@/components/ui/Breadcrumb";
import AupText from "@/components/ui/AupText";

export const metadata = { title: "Analysis Facility - Acceptable Use Policy" };

export default function Aup() {
  return (
    <section>
      <div className="container">
        <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "AUP" }]} />
        <h4 className="text-center mb-4">Acceptable Use Policy</h4>
        <AupText />
      </div>
    </section>
  );
}
