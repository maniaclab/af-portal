# Instructions to Connect VSCode to JupyterLab Kernel from UC AF

You can follow these steps to connect your Visual Studio Code to a JupyterLab
kernel that is running on the University of Chicago Analysis Facility (UC AF).
This allows you to work on your Jupyter notebooks using VS Code while utilizing
the computational resources of UC AF.

## Steps

1. **Access Your JupyterLab**:
   - Visit [UC AF JupyterLab](https://af.uchicago.edu/jupyterlab) to access your
     JupyterLab environment.
   - You'll need to log in with your credentials and create your Jupyter server.

2. **Get the JupyterLab URL**:
   - Right click on the link to your JupyterLab instance, then copy it. This
     link typically looks like
     `https://ivukotic-notebook-1.notebook.af.uchicago.edu/?token=...`.

3. **Configure VS Code**:
   - Open Visual Studio Code.
   - Install the **Python** and **Jupyter** extensions if you haven't already.

4. **Select Your Server and Kernel**:
   - Open the notebook file you wish to work on in VS Code.
   - Click on the kernel picker in the top right corner of the notebook editor
   - Click the kernel dropdown → click "Select Another Kernel..." → then
     "Existing Jupyter Server...".
   - Paste your server URI there.
   - Select the kernel you want to use from your JupyterLab.

5. **Using the Remote Kernel**:
   - Once the correct Kernel is selected, you can execute your notebook code
     within VS Code, utilizing the UC AF's computational resources.
   - If you encounter issues, ensure that VS Code is allowed through your
     firewall if applicable, and your network allows communicating with the UC
     AF nodes.

Enjoy coding with the power of UC AF directly from VS Code!

## Notes

- Make sure your JupyterLab instance is running and remains active while you are
  using VS Code to connect.

---
