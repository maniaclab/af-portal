export default function SshKeyInstructions() {
  return (
    <>
      <h4 className="mb-3">Instructions:</h4>
      <div className="mb-3">
        Fields with an <span className="asterisk">*</span> are required.
      </div>
      <div className="card mb-3">
        <div className="card-header bg-transparent">
          <a
            className="text-decoration-none"
            data-bs-toggle="collapse"
            href="#copypastekey"
            role="button"
            aria-expanded="false"
            aria-controls="copypastekey"
          >
            Already have a public key?
            <i className="fa-solid fa-info-circle float-end"></i>
          </a>
        </div>
        <div className="collapse card-body" id="copypastekey">
          <ol className="ps-4">
            <li className="mb-1">
              To find out, open your terminal and type:{" "}
              <kbd>ls ~/.ssh</kbd>
            </li>
            <li className="mb-1">
              If there is a .pub extension, such as id_rsa.pub, that is your
              SSH key.
            </li>
            <li className="mb-1">
              Type: <kbd>cat ~/.ssh/id_rsa.pub</kbd> in order to see your key.
            </li>
            <li className="mb-1">Copy the selection to the clipboard.</li>
            <li className="mb-1">
              Paste the contents of the clipboard in the corresponding box.
              Please only paste the public key (ending in .pub).
            </li>
          </ol>
        </div>
      </div>
      <div className="card mb-3">
        <div className="card-header bg-transparent">
          <a
            className="text-decoration-none"
            data-bs-toggle="collapse"
            href="#generatekey"
            role="button"
            aria-expanded="false"
            aria-controls="generatekey"
          >
            Generate a new public key
            <i className="fa-solid fa-info-circle float-end"></i>
          </a>
        </div>
        <div className="collapse card-body" id="generatekey">
          <ol className="ps-4">
            <li className="mb-1">
              In a terminal, type: <kbd>ssh-keygen -t rsa</kbd>
            </li>
            <li className="mb-1">
              Hit enter for the default location, and optionally enter a
              password. This will generate two files: A private key file
              (typically id_rsa) and a public key file (typically id_rsa.pub).
              The private key should never be shared, and ATLAS Analysis
              Facility will never ask you for your private key.
            </li>
            <li className="mb-1">
              In order to see your SSH public key type: <br />
              <kbd>cat ~/.ssh/id_rsa.pub</kbd>
            </li>
            <li className="mb-1">
              Use your mouse to select everything that is printed to the screen.
              The format should look like:{" "}
              <span className="text-muted">
                ssh-rsa AAAAB3N....M7Q== yourusername@yourmachine
              </span>
            </li>
            <li className="mb-1">Copy the selection to the clipboard.</li>
            <li className="mb-1">
              Paste the contents of the clipboard in the corresponding box.
            </li>
          </ol>
        </div>
      </div>
    </>
  );
}
