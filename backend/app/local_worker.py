"""Single local worker, durable DB queue; browser-independent while host is awake."""
import time
import logging
from .service import poll_jobs

def main():
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            poll_jobs()
        except Exception:
            logging.exception('Worker cycle failed')
        time.sleep(15)

if __name__ == '__main__': main()
