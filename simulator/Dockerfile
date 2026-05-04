FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && apt-get install -y -qq \
    curl openssh-client nmap netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*
COPY attacker.sh /attacker.sh
RUN chmod +x /attacker.sh
CMD ["/attacker.sh"]
