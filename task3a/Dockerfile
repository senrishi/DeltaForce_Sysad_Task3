FROM ubuntu:latest
WORKDIR /not_discord

RUN apt update && \
    apt install -y python3 python3-pip postgresql-16 postgresql-client-16 
RUN pip3 install psycopg2

COPY . .
EXPOSE 5005
CMD ["python3", "-u", "server_side.py"]
