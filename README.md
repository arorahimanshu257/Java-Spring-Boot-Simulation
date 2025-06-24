# FORCE-PLATFORM-API-PIPELINE

## Table of Contents
1. [Changes Made in CrewAI Package](#changes-made-in-crewai-package)

## Development Environment Setup Guide

2. [Prerequisites](#prerequisites)
3. [Initial System Setup](#initial-system-setup)
4. [Repository Structure](#repository-structure)
5. [Development Tools Installation](#development-tools-installation)
6. [Environment Configuration](#environment-configuration)
7. [Repository Setup](#repository-setup)
8. [Local Development Workflow](#local-development-workflow)

## Changes Made in CrewAI Package

Below are the details of the changes made to the CrewAI package, including file locations, modified lines, and a brief description of the updates:

| **File Location**                            | **Lines**                           | **Description**                                                                 |
|----------------------------------------------|-------------------------------------|---------------------------------------------------------------------------------|

| `crewai/utilities/events/llm_events.py`      | 18                                 | Changed from str to Any to fix the validation error for multimodal
| `crewai/tools/structured_tool.py `           | 183,184                            | Added these lines to fix the nl2sql built in bug in which it uses query insted of sql query 
| `crewai/tools/agent_tools/add_image_tool.py` | 33-41                              | Handling local file path in the built in Add image tool

| `crewai_tools/tools/file_writer_tool/file_writer_tool.py` | 7,13,19-25,30-36      | Added a directory parameter and set it to execution id

| `crewai/agents/parser.py`                                 | 78,79                 | Added Redis integration for loggin functionality

| `crewai/utilities/printer.py`                             | 11,12                 | Added Redis integration for loggin functionality

## Important Note:

Memory is not yet supported with our currently deployed `Google Vertex AI Embeddings Models`.



## **Prerequisites**

#### Minimum Hardware Requirements
- **Ram** 8GB and More 
- At least 50GB free disk space
- Multi-core processor (4+ cores recommended)

#### Operating System Requirements
- Windows 10/11, macOS (10.15+), or Linux (Ubuntu 20.04+ recommended)

#### Other Requirements
- Basic knowledge of Git commands
- Access to company VPN (if required)
- Access to organization's ADO and DA Admin Portal



## **Initial System Setup**


#### Required Software
- **Git** (latest version)
- **Python** 3.10+
- **Postman** for API Testing
- **PGAdmin/DBeaver** for DB client
- **Docker Desktop** (Optional)


### IDE Recommendations
- **VS Code** for Python 
- **PyCharm** & **Anaconda** (optional for Python development)

### Installation Instructions

### Python Installation Setup

#### Windows

1. **Download Python**:
   - Visit the official Python website: [https://www.python.org/downloads/](https://www.python.org/downloads/).
   - Download the latest Python version (Python 3.x).


3. **Verify Installation**:
   - Open Command Prompt (`cmd`).
   - Run the command:
     ```bash
     python --version
     ```
   - You should see the installed version of Python.

#### Linux (Ubuntu)

2. **Install Python 3**:
   - Install Python using the following command:
     ```bash
     sudo apt install python3
     ```

3. **Install `pip` (Python package manager)**:
   - Run the following command to install `pip`:
     ```bash
     sudo apt install python3-pip
     ```

4. **Verify Installation**:
   - Check the Python version:
     ```bash
     python3 --version
     ```

#### macOS
2. **Install Python 3**:
   - Install Python using Homebrew:
     ```bash
     brew install python
     ```

3. **Verify Installation**:
   - Check the Python version:
     ```bash
     python3 --version
     ```

### Postman

1. **Download Postman**:
   - Visit the official Postman website: [https://www.postman.com/downloads/](https://www.postman.com/downloads/).
   - Download and install Postman for your operating system.

2. **Use Postman**:
   - Use Postman for API testing and making HTTP requests to your APIs.

### Docker Desktop

1. **Download Docker Desktop**:
   - Visit [Docker’s official website](https://www.docker.com/products/docker-desktop) and download Docker Desktop for your OS (Windows/Mac).

2. **Install Docker**:
   - Follow the installation steps for your operating system.
   - After installation, ensure Docker is running by checking the Docker icon in your system tray.

3. **Verify Installation**:
   - Run the following command in a terminal:
     ```bash
     docker --version
     ```


## **Repository Structure**

```
force-platform-api-pipeline/

|
├── /helpers
│   ├── /helpers.py
|   └── /logger_config.py  
|   └── /redis_client.py
|   └── /secret_manager.py
|   └── /db_uri.py
|   └── /agent_image_utils.py
|  
|   
|
├──/modified_library
|   └── /add_image_tool.py
|   └── /file_writer_tool.py
|   └── /llm_events.py
|   └── /parser.py
|   └── /printer.py
|   └── /structured_tool.py
|
├──/PipelineModel
|             ├──/PipelineLogs
|             ├──/Tools
|             ├── agent.py
|             ├── agentDetails.py 
|             ├── agentEmbedding.py
|             ├── agentLLM.py 
|             ├── AgentToolParams.py
|             ├── AgentTools.py
|             ├── langfuse.py
|             ├── Message.py
|             ├── PipelineModel.py
|             ├── PipelineRequest.py
|             ├── ResponseModel.py
|             ├── taskDetails.py
|             └── TaskOutputModel.py
|
├──/tools
|       ├──/filereadtool.py
|       ├──/sqltool.py
|  
|
|──/AVASecret.py
|
|──/azure-pipelines.yml
|
├──/docker-compose.yml
|
├──/Dockerfile 
|
├──/genai-platform-creds.json
|
├──/knowledgeRagTool.py
|
├──/pipeline_ai.py
|
├──/pipeline_files.py
|
├──/README.md
|
|──/redis_logs.py
│
└──/requirements.txt

```
- **docker-compose.yml**: Configures and runs the Force Platform API container with required settings.  

- **Dockerfile**: Configures a lightweight Python 3.12 container with required dependencies, environment variables, and a FastAPI app running on Uvicorn.  


- **pipeline_ai.py**: Entry point for the service, defining all REST APIs for the application. 

- **PipelineModel**: Contains all essential components like request/response, models, tools, and agents used in the pipeline's execution.  

- **requirements.txt**: Lists all the Python dependencies required for the project, which can be installed using `pip`.

## **Development Tools Installation**

### IDE Setup

> **Note:**  
> You can also use **PyCharm** IDE for efficient Python development with advanced features.


#### VS Code

1. **Install VS Code**:
   - Download and install Visual Studio Code from [https://code.visualstudio.com/](https://code.visualstudio.com/).

2. **Install VS Code Extensions**:
   - Once VS Code is installed, open it and go to the Extensions Marketplace (View > Extensions).
   - Install the following extensions:
     - **Python**: Provides Python language support and features like IntelliSense, linting, and debugging.
     - **Pylance**: Enhances Python language features such as type checking and fast IntelliSense.

     - **Docker**: Helps manage Docker containers and images from within VS Code.


## **Environment Configuration**

1. **Create a Virtual Environment**:
   - To create a virtual environment:
     ```bash
     python -m venv myenv
            
            #or

     python3 -m venv myenv
     ```

2. **Activate the Virtual Environment**:
   - On Windows:
     ```bash
     myenv\Scripts\activate
     ```
   - On Linux/macOS:
     ```bash
     source myenv/bin/activate
     ```

3. **Deactivate the Virtual Environment**:
   - To deactivate the virtual environment, run:
     ```bash
     deactivate
     ```

## **Repository Setup**

#### Cloning Repositories
1. Create a project directory:
    ```bash
    mkdir project-name
    cd project-name
    ```

2. Clone repositories:
    ```bash
    git clone <python-repo-url>
    ```

### Initial Setup for Each Repository

#### Python API:
1. Navigate to the `force-platform-api-pipeline` directory:
    ```bash
    cd force-platform-api-pipeline
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    # or
    poetry install
    ```

## **Local Development Workflow**

### Branch Management

1. **Create a feature branch from `development/main/master`:**
    ```bash
    git checkout -b <your-feature-branch>
    ```

2. **Regular sync with `development/main` branch:**
    ```bash
    git pull origin development
    git checkout <your-feature-branch>
    git merge development
    ```

### Python API

1. **From `force-platform-api-pipeline` directory:**
    ```bash
    uvicorn pipeline_ai:app
    ```

### Testing

- Run unit tests before committing.
- Ensure all services are running locally.
- Test API endpoints using Postman.
- Verify UI changes in different browsers.

### Code Commit Process

1. **Check changed files:**
    ```bash
    git status
    ```

2. **Add files:**
    ```bash
    git add .
    ```

3. **Commit with a meaningful message:**
    ```bash
    git commit -m " your message "
    ```

4. **Push changes:**
    ```bash
    git push origin <your-feature- branch>
    ```

### Pull Request Process

1. Create a PR through the ADO/GitHub/GitLab interface.
2. Fill in the PR template.
3. Add relevant reviewers.
4. Address review comments.
5. Update the branch if needed.
6. Await approval and merge.

