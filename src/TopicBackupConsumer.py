#
# Kafka consumer that backups the topic messages
#

import signal
from confluent_kafka import Consumer, TopicPartition
from Storage import Storage
from utils import offsetToStr
from struct import *

TOPIC_LIST = ['test-topic-2', 'test-topic-1']
BOOTSTRAP_SERVERS = 'localhost:29092'


class TopicBackupConsumer:

    consumer = None
    exit_task = False

    def __init__(self, topics_to_backup = None, stream = Storage('backup')):
        self.topics_list = topics_to_backup
        self.stream = stream

    # Consumer callbacks

    def on_assign(self, consumer, partitions):
        partitions = consumer.committed(partitions) # Get the real offsets
        print('on_assign:', [f'{p.topic}/{p.partition} offset={offsetToStr(p.offset)}' for p in partitions])

    def on_revoke(self, consumer, partitions):
        print('on_revoke:', [f'{p.topic}/{p.partition} offset={offsetToStr(p.offset)}' for p in partitions])

    def on_lost(self, consumer, partitions):
        print('on_revoke:', [f'{p.topic}/{p.partition} offset={offsetToStr(p.offset)}' for p in partitions])

    # Tasks control

    def stop(self):
        print('Stop signal received')
        self.exit_task = True

    def start(self, topics_to_backup = None):

        if topics_to_backup != None:
            self.topics_list = topics_to_backup

        consumer = Consumer({
            'group.id': 'kafka-backup-topic',
            'bootstrap.servers': BOOTSTRAP_SERVERS,
            'auto.offset.reset': 'smallest',
            'enable.auto.commit': False
        })

        consumer.subscribe(self.topics_list, on_assign=self.on_assign, on_revoke=self.on_revoke, on_lost=self.on_lost)

        while True:
            messages = consumer.consume(timeout=3) # Get messages in batch

            if self.exit_task:
                break

            # if len(messages) == 0:
            #     print('Timeout without messages')

            for m in messages:
                if m.error():
                    print('Message error', m.error())
                else:
                    # Valid message
                    # print(f'{m.topic()}:{m.partition()} {m.offset()}')
                    self.stream.backup_message(m)

                    consumer.commit(message=m) # TODO: Use the offsets instead
                    # consumer.commit(offsets=[TopicPartition(m.topic(), m.partition(), m.offset())]) # TODO: Use the offset

        print('Stopping task')
        consumer.close()
        self.stream.close()


if __name__ == "__main__":
    # Capture interrupt to clean exit
    def signal_handler(sig, frame):
        global a
        a.stop()
    signal.signal(signal.SIGINT, signal_handler)

    a = TopicBackupConsumer(TOPIC_LIST)
    a.start()
