# Stage 1: Build environment
FROM ubuntu:24.04 AS builder

# Avoid prompts during apt installations
ENV DEBIAN_FRONTEND=noninteractive

# Create a non-root user and set up their home directory
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin appuser && \
    mkdir -p /app && \
    chown appuser:appuser /app

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for building and running the app
RUN apt-get update && apt-get install -y \                  
    wget \                            
    build-essential \                 
    curl \                            
    ca-certificates \                 
    libpq-dev \                      
    python3-dev \                     
    default-libmysqlclient-dev \     
    pkg-config \                      
    && rm -rf /var/lib/apt/lists/*    

# Install Miniconda for managing Python environments
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh \
    && mkdir /root/.conda \           
    && bash miniconda.sh -b -p /opt/conda \         
    && rm miniconda.sh                

# Add Conda to the PATH environment variable
ENV PATH="/opt/conda/bin:${PATH}"

# Create a new Conda environment named 'env' with Python 3.12
RUN conda create --name env python=3.12 -y && conda clean -afy

# Set permissions for conda environment
RUN chown -R appuser:appuser /opt/conda

# Switch to non-root user
USER appuser

# Set the default shell to run commands within the conda environment
SHELL ["conda", "run", "-n", "env", "/bin/bash", "-c"]

# Copy Python dependency list into the container
COPY --chown=appuser:appuser requirements.txt /app

# Upgrade pip and install Python dependencies from requirements.txt
RUN pip install --upgrade pip && \
    conda install pip -y && \                                 
    (conda install --file requirements.txt -y || \            
     pip install --use-pep517 -r requirements.txt) && \       
    conda clean -afy                                          

# Install langchain-google-vertexai manually (not in requirements.txt due to conflicts with protobuf)
RUN pip install langchain-google-vertexai

# Install specific version of PyPDF manually (not in requirements.txt due to conflicts with llama-index)
# RUN pip install pypdf==5.1.0

# Clean up unnecessary files from site-packages to reduce final image size
RUN find /opt/conda/envs/env/lib/python3.12/site-packages -name "*.pyc" -delete && \
    find /opt/conda/envs/env/lib/python3.12/site-packages -name "*.pyo" -delete && \
    find /opt/conda/envs/env/lib/python3.12/site-packages -name "tests" -type d -exec rm -rf {} + && \
    find /opt/conda/envs/env/lib/python3.12/site-packages -name "__pycache__" -type d -exec rm -rf {} +

# Copy all application source code into the container
COPY --chown=appuser:appuser . /app

# Stage 2: Final runtime environment
FROM ubuntu:24.04

# Avoid prompts during apt installations
ENV DEBIAN_FRONTEND=noninteractive

# Create the same non-root user as in builder stage
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin appuser && \
    mkdir -p /app && \
    chown appuser:appuser /app

# Set the working directory inside the container
WORKDIR /app

# Install only minimal required system dependencies for runtime
RUN apt-get update && apt-get install -y \
    ca-certificates \
    default-jre \
    dos2unix \          
    && rm -rf /var/lib/apt/lists/*

# Copy the prepared Conda environment from the builder stage
COPY --from=builder --chown=appuser:appuser /opt/conda /opt/conda

# Copy the application code from the builder stage
COPY --from=builder --chown=appuser:appuser /app /app

RUN cp /app/modified_library/printer.py /opt/conda/envs/env/lib/python3.12/site-packages/crewai/utilities/ && \
    cp /app/modified_library/parser.py /opt/conda/envs/env/lib/python3.12/site-packages/crewai/agents/ 

COPY genai-platform-creds.json /app/genai-platform-creds.json
# Set environment variables
ENV LOG_LEVEL=debug
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/genai-platform-creds.json"

# Add Conda environment to PATH
ENV PATH="/opt/conda/bin:${PATH}"

# Copy and set up the start script
COPY start.sh /app/start.sh
RUN dos2unix /app/start.sh && \
    chmod +x /app/start.sh
 
# Switch to non-root user
USER appuser

# Set shell to always run inside the 'env' conda environment
SHELL ["conda", "run", "-n", "env", "/bin/bash", "-c"]

# Expose the application's port
EXPOSE 8080

# Change the ENTRYPOINT to use the script
ENTRYPOINT ["/app/start.sh"]

# Launch the application using Uvicorn as the ASGI server
# ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "env", "uvicorn pipeline_ai:app --workers ${FUNCTIONS_WORKER_PROCESS_COUNT:-10} --host 0.0.0.0 --port 8080 --loop asyncio --timeout-keep-alive 6000 --log-level debug"]
# ENTRYPOINT ["/bin/sh", "-c", "/opt/venv/bin/uvicorn pipeline_ai:app --workers ${FUNCTIONS_WORKER_PROCESS_COUNT:-10} --host 0.0.0.0 --port 8080 --loop asyncio --timeout-keep-alive 6000 --log-level debug"]