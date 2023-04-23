import socket
import logging
from dnslib import DNSRecord, A, AAAA, CNAME, MX, NS, RR, DNSHeader, DNSQuestion, QTYPE
import json
import settings
from typing import List, Dict, Optional


logging.basicConfig(
    filename="log/server.log",
    format="%(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


class DNSServer:
    def __init__(
        self, host: str = "127.0.0.1", port: int = 53, buffer_size: int = 1024
    ):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.socket = None
        self.records = self.__load_records()

    def create(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logging.info("Socket created")
        self.socket.bind((self.host, self.port))
        logging.info(f"Bound to {self.host}:{self.port}")

    def start(self):
        while True:
            try:
                message, address = self.socket.recvfrom(self.buffer_size)
                dns_query = DNSRecord.parse(message)
                response = self.__lookup(dns_query)
                self.socket.sendto(response, address)
                logging.info("Response returned")
            except Exception as e:
                logging.error(e)

    def destroy(self):
        self.socket.close()
        logging.info("Socket destroyed")

    def __load_records(self) -> Dict:
        with open("zones/dns.json") as fp:
            try:
                return json.load(fp)
            except Exception as e:
                logging.error(f"Failed to load zones JSON: {e}")
                return dict()

    def __extract_domain_from_labels(self, question: DNSQuestion) -> str:
        return ".".join([label.decode() for label in question._qname.label])

    def __extract_query_type(self, question: DNSQuestion) -> str:
        return QTYPE.get(question.qtype, "UNKNOWN")

    def __get_mx_records(
        self, domain_records: List[Dict], mx_domain: str
    ) -> Optional[str]:
        for mx_record in domain_records:
            if mx_record.get("type", "") == "A" and mx_record.get("name") == mx_domain:
                return mx_record.get("value")
        return None

    def __lookup(self, dns_query: DNSRecord) -> bytearray:

        question = dns_query.questions[0]
        logging.info(f"{question=}")

        domain = self.__extract_domain_from_labels(question)
        if domain[-1] != ".":
            domain += "."
        query_type = self.__extract_query_type(question)

        domain_records = self.records.get(domain, [])
        response = DNSRecord(
            DNSHeader(id=dns_query.header.id, qr=1, aa=1, ra=1), q=DNSQuestion(domain),
        )

        for record in domain_records:

            if record.get("type") == query_type:

                if query_type == "A" and record.get("name") == domain:
                    value = record.get("value")
                    if value is not None:
                        response.add_answer(RR(domain, rdata=A(value), ttl=60))

                # ! ERROR: Got bad packet: extra input data
                elif query_type == "MX":
                    value = record.get("value")
                    try:
                        priority, mx_domain = value.strip().split()
                        response.add_answer(RR(domain, rdata=MX(value), ttl=60))

                        value = self.__get_mx_records(domain_records, mx_domain)
                        response.add_answer(RR(mx_domain, rdata=A(value), ttl=60))

                    except Exception as e:
                        logging.error(e)
                        response.add_answer(RR(domain, rdata=MX(value), ttl=60))

        return response.pack()


def main():
    server_socket = DNSServer(host=settings.HOST, port=settings.PORT)
    server_socket.create()
    server_socket.start()
    server_socket.destroy()


main()
