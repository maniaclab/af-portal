import Breadcrumb from "@/components/ui/Breadcrumb";
import AupText from "@/components/ui/AupText";
import SignupModal from "@/components/ui/SignupModal";

export const metadata = { title: "Analysis Facility - Signup" };

export default function Signup() {
  return (
    <>
      <section>
        <div className="container col-lg-10">
          <Breadcrumb
            items={[{ label: "Home", href: "/" }, { label: "Signup" }]}
          />
          <h4 className="text-center mb-4">
            Sign up for ATLAS Analysis Facility at UChicago
          </h4>
          <p>
            To create an account, please use your home institution&apos;s login
            service. (You can use CERN&apos;s if your institution is not
            listed.) In either case, please make sure to list your home
            institution in your user profile (https://af.uchicago.edu/profile).
            Your request will be sent to the UC ATLAS Analysis Facility support
            team.
          </p>
          <a
            href="/auth/login"
            role="button"
            className="btn btn-sm btn-primary"
          >
            Continue
          </a>

          <div
            className="modal fade"
            id="myModal"
            tabIndex={-1}
            aria-labelledby="myModalLabel"
            aria-hidden="true"
          >
            <div className="modal-dialog modal-lg">
              <div className="modal-content">
                <div className="modal-header">
                  <h5 className="modal-title" id="myModalLabel">
                    Acceptable Use Policy
                  </h5>
                  <button
                    type="button"
                    className="btn-close"
                    data-bs-dismiss="modal"
                    aria-label="Close"
                  />
                </div>
                <div className="modal-body" style={{ overflowY: "auto", maxHeight: "60vh" }}>
                  <AupText />
                </div>
                <div className="modal-footer">
                  <button
                    type="button"
                    className="btn btn-primary"
                    data-bs-dismiss="modal"
                  >
                    Agree
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      <SignupModal />
    </>
  );
}
