FROM ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest

USER root
WORKDIR /home/computeruse

# API dependencies (FastAPI etc.)
COPY requirements.txt /home/computeruse/api_requirements.txt
RUN pip install -r /home/computeruse/api_requirements.txt

# App source
COPY app /home/computeruse/app
COPY frontend /home/computeruse/frontend
COPY entrypoint_api.sh /home/computeruse/entrypoint_api.sh
RUN chmod +x /home/computeruse/entrypoint_api.sh

ENV PYTHONPATH=/home/computeruse:/home/computeruse/app:/home/computeruse/computer_use_demo

EXPOSE 8000 6080 5900

USER computeruse

ENTRYPOINT ["/home/computeruse/entrypoint_api.sh"]


