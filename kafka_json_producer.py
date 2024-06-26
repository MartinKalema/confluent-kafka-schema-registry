from uuid import uuid4
from confluent_kafka import Producer
from confluent_kafka.serialization import StringSerializer, SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONSerializer
import pandas as pd
from typing import List
from dotenv import load_dotenv
import os

load_dotenv()


FILE_PATH = "/home/kalema/Projects/data-engineering/confluent-kafka-schema-registry/cardekho_dataset.csv"
columns=['car_name', 'brand', 'model', 'vehicle_age', 'km_driven', 'seller_type',
       'fuel_type', 'transmission_type', 'mileage', 'engine', 'max_power',
       'seats', 'selling_price']

API_KEY = os.getenv('API_KEY')
ENDPOINT_SCHEMA_URL  = os.getenv('ENDPOINT_SCHEMA_URL')
API_SECRET_KEY = os.getenv('API_SECRET_KEY')
BOOTSTRAP_SERVER = os.getenv('BOOTSTRAP_SERVER')
SECURITY_PROTOCOL = os.getenv('SECURITY_PROTOCOL')
SSL_MACHENISM = os.getenv('SSL_MACHENISM')
SCHEMA_REGISTRY_API_KEY = os.getenv('SCHEMA_REGISTRY_API_KEY')
SCHEMA_REGISTRY_API_SECRET = os.getenv('SCHEMA_REGISTRY_API_SECRET')

# Kafka cluster connectivity
def sasl_conf():
    sasl_conf = {'sasl.mechanism': SSL_MACHENISM,
                 # Set to SASL_SSL to enable TLS support.
                #  'security.protocol': 'SASL_PLAINTEXT'}
                'bootstrap.servers':BOOTSTRAP_SERVER,
                'security.protocol': SECURITY_PROTOCOL,
                'sasl.username': API_KEY,
                'sasl.password': API_SECRET_KEY
                }
    return sasl_conf


# Schema registry connectivity
def schema_config():
    return {'url':ENDPOINT_SCHEMA_URL,
    
    'basic.auth.user.info':f"{SCHEMA_REGISTRY_API_KEY}:{SCHEMA_REGISTRY_API_SECRET}"

    }

class Car:   
    def __init__(self,record:dict):
        for k,v in record.items():
            setattr(self,k,v)
        
        self.record=record
   
    @staticmethod
    def dict_to_car(data:dict,ctx):
        return Car(record=data)

    def __str__(self):
        return f"{self.record}"


def get_car_instance(file_path):
    df=pd.read_csv(file_path)
    df=df.iloc[:,1:]
    cars:List[Car]=[]
    for data in df.values:
        car=Car(dict(zip(columns,data)))
        cars.append(car)
        yield car

def car_to_dict(car:Car, ctx):
    """
    Returns a dict representation of a User instance for serialization.
    Args:
        user (User): User instance.
        ctx (SerializationContext): Metadata pertaining to the serialization
            operation.
    Returns:
        dict: Dict populated with user attributes to be serialized.
    """

    # User._address must not be serialized; omit from dict
    return car.record


def delivery_report(err, msg):
    """
    Reports the success or failure of a message delivery.
    Args:
        err (KafkaError): The error that occurred on None on success.
        msg (Message): The message that was produced or failed.
    """

    if err is not None:
        print("Delivery failed for User record {}: {}".format(msg.key(), err))
        return
    print('User record {} successfully produced to {} [{}] at offset {}'.format(
        msg.key(), msg.topic(), msg.partition(), msg.offset()))


def main(topic):

#     schema_str = """
#     {
#   "$id": "http://example.com/myURI.schema.json",
#   "$schema": "http://json-schema.org/draft-07/schema#",
#   "additionalProperties": false,
#   "description": "Sample schema to help you get started.",
#   "properties": {
#     "brand": {
#       "description": "The type(v) type is used.",
#       "type": "string"
#     },
#     "car_name": {
#       "description": "The type(v) type is used.",
#       "type": "string"
#     },
#     "engine": {
#       "description": "The type(v) type is used.",
#       "type": "number"
#     },
#     "fuel_type": {
#       "description": "The type(v) type is used.",
#       "type": "string"
#     },
#     "km_driven": {
#       "description": "The type(v) type is used.",
#       "type": "number"
#     },
#     "max_power": {
#       "description": "The type(v) type is used.",
#       "type": "number"
#     },
#     "mileage": {
#       "description": "The type(v) type is used.",
#       "type": "number"
#     },
#     "model": {
#       "description": "The type(v) type is used.",
#       "type": "string"
#     },
#     "seats": {
#       "description": "The type(v) type is used.",
#       "type": "number"
#     },
#     "seller_type": {
#       "description": "The type(v) type is used.",
#       "type": "string"
#     },
#     "selling_price": {
#       "description": "The type(v) type is used.",
#       "type": "number"
#     },
#     "transmission_type": {
#       "description": "The type(v) type is used.",
#       "type": "string"
#     },
#     "vehicle_age": {
#       "description": "The type(v) type is used.",
#       "type": "number"
#     }
#   },
#   "title": "SampleRecord",
#   "type": "object"
# }
#     """
    
    # client object
    schema_registry_client = SchemaRegistryClient(schema_config()) 

    # key serializer
    string_serializer = StringSerializer('utf_8') 

    # latest schema
    schema = schema_registry_client.get_schema(schema_registry_client.get_latest_version(topic + "-value").schema_id)


    json_serializer = JSONSerializer(schema.schema_str, schema_registry_client, car_to_dict)


    producer = Producer(sasl_conf())

    print("Producing user records to topic {}. ^C to exit.".format(topic))
    #while True:
        # Serve on_delivery callbacks from previous calls to produce()
    producer.poll(5.0)
    try:
        for car in get_car_instance(file_path=FILE_PATH):

            print(car)
            producer.produce(topic=topic,
                            key=string_serializer(str(uuid4()), car_to_dict),
                            value=json_serializer(car, SerializationContext(topic, MessageField.VALUE)),
                            on_delivery=delivery_report)
    except KeyboardInterrupt:
        pass
    except ValueError:
        print("Invalid input, discarding record...")
        pass

    print("\nFlushing records...")
    producer.flush() 

main("topic_0")