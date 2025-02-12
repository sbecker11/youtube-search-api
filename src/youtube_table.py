# pylint: disable=C0103 # Invalid name

import json
import logging
import os
from typing import Dict, Any, List, Optional

import boto3
import botocore
from boto3.resources.base import ServiceResource

from dynamodb_utils.item_utils import DynamoDbItemPreProcessor
from dynamodb_utils.filter_utils import DynamoDbFilterUtils
from dynamodb_utils.dbtypes import *

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeTableException(Exception):
    pass

class YouTubeTable:

    try:
        dynamodb_url = os.getenv('DYNAMODB_URL')
        dynamodb_client = boto3.client('dynamodb', endpoint_url=dynamodb_url)
        dynamodb_resource = boto3.resource('dynamodb', endpoint_url=dynamodb_url)

    except boto3.exceptions.Boto3Error as error:
        logger.error("class initialization error: %s", {error})
        raise

    def __init__(self, table_config: Dict[str, str]):
        try:
            self.table_config = table_config
            self.table_name = self.table_config['TableName']
            self.dbTable = YouTubeTable.find_dbTable_by_name(self.table_name)
            if not self.dbTable:
                self.dbTable = YouTubeTable.create_dbTable(self.table_config)

            self.item_preprocessor = DynamoDbItemPreProcessor(self.table_config)

            # initialize the batch list
            self.reset_batch()

        except boto3.exceptions.Boto3Error as error:
            print(f"Error initializing DynamoDb resource: {error}")
            raise
        except FileNotFoundError as error:
            print(f"Configuration file not found: {error}")
            raise
        except json.JSONDecodeError as error:
            print(f"Error decoding JSON configuration: {error}")
            raise

        logger.info("YouTubeTable '%s' successfully initialized", self.table_name)

    def dbTable_exists(self):
        """
        Check if the dynamoDb table already exists.

        :return: True if the dynamoDb table exists, False otherwise.
        """
        try:
            self.dynamodb_client.describe_table(TableName=self.table_name)
            return True
        except self.dynamodb_client.exceptions.ResourceNotFoundException:
            return False
        except Exception as error:
            print(f"Error checking if dynamoDb table exists: {error}")
            raise

    def get_dbTable_config(table_name):
        table_description = YouTubeTable.dynamodb_resource.describe_table(TableName=table_name)
        tableNameText = f"\"{table_name}\""
        keySchema = table_description['Table']['KeySchema']
        keySchemaText = DynamoDbJsonUtils.json_dumps(keySchema,indent=4)
        attrDefs = table_description['Table']['AttributeDefinitions']
        attrDefsText = DynamoDbJsonUtils.json_dumps(attrDefs,indent=4)
        provThruPut = table_description['Table']['ProvisionedThroughput']
        provThruPutText = DynamoDbJsonUtils.json_dumps(provThruPut,indent=4)

        configs = []
        configs.append(f"   \"TableName\": {tableNameText}")
        configs.append(f"   \"KeySchema\": {keySchemaText}")
        configs.append(f"   \"AttributeDefinitions\": {attrDefsText}")
        configs.append(f"   \"ProvisionedThroughput\": {provThruPutText}")
        config_text = "{\n" + ",\n".join(configs) + "\n}"

        dbTable_config = json.loads(config_text)
        return dbTable_config

    def get_table_name(self) -> str:
        return self.table_name

    def get_preprocessed_item(self, item: DbItem) -> DbItem:
        return self.item_preprocessor.get_preprocessed_item(item)

    @classmethod
    def find_dbTable_by_name(cls, table_name: str) -> DbTable:
        """
        Find a DynamoDb table by its name, or return None

        :param table_name: The name of the table to check for existence.
        :return: The table if it exists, None otherwise.
        """
        found_dbTable = None
        try:
            # Attempt to describe the table. If this succeeds, the table exists.
            cls.dynamodb_client.describe_table(TableName=table_name)
            found_dbTable = cls.dynamodb_resource.Table(table_name)
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'ResourceNotFoundException':
                found_dbTable = None
            else:
                logger.error("An error occurred while checking for table %s: %s", table_name, error)
                return None
            # If the table doesn't exist, we'll get this exception.
            found_dbTable = None
        except boto3.exceptions.Boto3Error as error:
            # Catch other exceptions and log them for debugging.
            print(f"An error occurred while checking for table {table_name}: {error}")
            found_dbTable = None

        return found_dbTable

    @classmethod
    def create_dbTable(cls, dbTable_config: Dict[str,Any]) -> DbTable:
        """
        Create a new DynamoDb table with the given configuration.

        The configuration should include:
        - TableName
        - KeySchema: Specifies the attributes that make up the primary key for the table.
        - AttributeDefinitions: An array of attributes that describe the key schema for the table and indexes.
        - ProvisionedThroughput: Specifies the read and write capacity units for the table.

        Example configuration:
        {
            "TableName": "Responses",
            "KeySchema": [
                {
                    "AttributeName": "id",
                    "KeyType": "HASH"
                }
            ],
            "AttributeDefinitions": [
                {
                    "AttributeName": "id",
                    "AttributeType": "S"
                }
            ],
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5
            }
        }
        """
        try:
            dbTable_name = dbTable_config["TableName"]
            new_dbTable = cls.dynamodb_resource.create_table(**dbTable_config)
            return new_dbTable
        except boto3.exceptions.Boto3Error as error:
            logger.error("An error occurred in create_dbTable table: %s: %s", dbTable_name, {error})
            raise

    @classmethod
    def add_item_to_dbTable(cls, item: DbItem, dbTable:DbTable):
        """
        Add a new DbItem to the dbTable.

        :param item: A dictionary representing the item to add.
        :param dbTable: that DbTable
        """
        try:
            dbTable.put_item(Item=item)
        except boto3.exceptions.Boto3Error as error:
            logger.error("An error occurred in add_item_to_dbTable: %s: %s", dbTable.table_name, {error})
            raise

    def add_item(self, item: DbItem):
        """
        Add a new DbItem to the dbTable of this YouTubeTable.
        """
        YouTubeTable.add_item_to_dbTable(item, self.dbTable)

    @classmethod
    def add_item_to_dbTable_batch(cls, dbTable_batch:List[DbItem], item: DbItem):
        """
        Add an item to the dbTable_batch.

        :param item: a DbItem which is a dict representing the item to add.
        """
        try:
            dbTable_batch.append(item)
        except boto3.exceptions.Boto3Error as error:
            logger.error("An error occurred in add_item_to_dbTable_batch for dbTable: %s: %s", dbTable.table_name, {error})
            raise


    @classmethod
    def flush_dbTable_batch(cls, dbTable_batch:List[DbItem], dbTable:DbTable):
        """
        Flush the DBItems of the given dbTable_batch to the given dbTable
        """
        num_items = len(dbTable_batch)
        if num_items == 0:
            logger.info("flush of empty dbTable_batch ignored")
            return
        try:
            logger.info("flushing %d items from dbTable_batch", num_items)
            with dbTable.batch_writer() as batch:
                for item in dbTable_batch:

                    print(f"putting item\n{json.dumps(item, indent=2)}")
                    batch.put_item(Item=item)

            dbTable_batch = []
        except boto3.exceptions.Boto3Error as error:
            logger.error("An error occurred in flush_dbTable_batch with %d items for dbTable: %s: %s",
                len(dbTable_batch), dbTable.table_name, {error})
            logger.info()
            raise

    def reset_batch(self):
        self.items_to_add = []

    def add_item_to_batch(self, item: DbItem):
        YouTubeTable.add_item_to_dbTable_batch(self.items_to_add, item)

    def flush_batch(self):
        """
        Flush the DBItems of the given items_to_add list of this YouTubeTable object
        """
        YouTubeTable.flush_dbTable_batch(self.items_to_add, self.dbTable)


    def get_item(self, key: DbItem) -> DbItem:
        """
        Retrieve a DbItem from the YouTubeTable.

        :param key: A dictionary representing the key of the item to retrieve.
        :return: The retrieved item.
        """
        try:
            response = self.dbTable.get_item(Key=key)
            return response.get('Item')
        except boto3.exceptions.Boto3Error as error:
            logger.error("An error occurred in get_item with key:%s for table: %s: %s", key, self.table_name, {error})
            raise

    def update_item(self, key: Dict[str,Any], update_expression: str, expression_attribute_values: Dict[str,Any]):
        """
        Update an item in the YouTubeTable.

        :param key: A dictionary representing the key of the item to update.
        :param update_expression: An update expression string.
        :param expression_attrerroribute_values: A dictionary of attribute values.
        """
        try:
            self.dbTable.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
        except boto3.exceptions.Boto3Error as error:
            logger.error("An error occurred in update_item with key:%s for table: %s: %s", key, self.table_name, {error})
            raise

    def delete_item(self, key: Dict[str,Any]):
        """
        Delete an item in the dbTable of this YouTubeTable.

        :param key: A dictionary representing the key of the item to delete.
        """
        try:
            self.dbTable.delete_item(Key=key)
        except boto3.exceptions.Boto3Error as error:
            logger.error("An error occurred in delete_item with key:%s for table: %s: %s", key, self.table_name, {error})
            raise

    def scan_table(self) -> List[DbItem]:
        """
        Return a list of all DbItems of the dbTable of this YouTubeTable

        Returns:
            List[DbItem]: all rows of the dbTable of this YouTubeTable
        """
        return self.scan_dbTable(self.dbTable)

    def count_table_items(self) -> int:
        """ Returns the count of all dbItem(rows) in the dbTable of this YouTubeTable """
        return YouTubeTable.count_dbTable_items(self.dbTable)

    def delete_table(self):
        """ delete this object's dbTable and remove this
            YouTubeTable's reference to that dbTable
        """
        self.delete_dbTable(self.dbTable)
        self.dbTable = None

    def select_dbItems_by_dbAttrs(self,
        dbItems:List[DbItem],
        select_by_dbAttrs:List[DbAttr]) -> List[DbItem]:
        return DynamoDbFilterUtils.select_dbItems_by_dbAttrs(dbItems, select_by_dbAttrs)

    def sort_dbItems_by_dbAttrs(self,
        dbItems:List[DbItem],
        sort_by_dbAttrs:List[Tuple[DbAttr, DbSortDir]]) -> List[DbItem]:
        return DynamoDbFilterUtils.sort_dbItems_by_dbAttrs(dbItems, sort_by_dbAttrs)

    def delete_dbTable(self, dbTable):
        if not dbTable_exists():
            logger.warning("delete_dbTable ignored: table %s does not exist", dbTable.table_name)
            return
        try:
            self.dbTable.delete()
            # Wait until the table is deleted
            self.dbTable.meta.client.get_waiter('table_not_exists').wait(TableName=self.table_name)
            logger.info("Table %s has been deleted.", self.table_name)
        except boto3.exceptions.Boto3Error as error:
            logger.error("An error occurred in delete table %s: %s", self.table_name, {error})
            raise


    def scan_dbTable(self, dbTable:DbTable) -> List[DbItem]:
        """
        Scan the entire DbTable.

        :return: A list of all DynamoDbItems in the DbTable.
        """
        try:
            response = dbTable.scan()
            return response.get('Items', [])
        except boto3.exceptions.Boto3Error as error:
            logger.error("An error occurred in scan_dbTable %s: %s", dbTable.table_name, {error})
            raise


    @classmethod
    def count_dbTable_items(cls, dbTable:DbTable) -> int:
        """
        return the number of items in this DbTable.

        :return: An integer count of the number of items in this dbTable.
        """
        try:
            total_items = 0
            response = dbTable.scan(Select='COUNT')

            while 'LastEvaluatedKey' in response:
                total_items += response['Count']
                response = dbTable.scan(ExclusiveStartKey=response['LastEvaluatedKey'], Select='COUNT')
            else: # pylint: disable=W0120 # Else clause on a loop without a break statement
                total_items += response['Count']

            return total_items
        except boto3.exceptions.Boto3Error as error:
            logger.eror("An error occurred in scan_dbTable %s: %s", dbTable.table_name, {error})
            raise




    @classmethod
    def dump_dbTable_to_json(cls, dbTable_name:str, json_file_path:str):
        """ find a dbTable by name and dump its contents to the given json_file_path
        """
        dbTable = cls.find_dbTable_by_name(dbTable_name)
        response = dbTable.scan()
        data = response['Items']
        logger.info("dumping %d items from table:%s to %s", len(data), dbTable_name, json_file_path)
        with open(json_file_path, 'w', encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4)
        logger.info("table:%s dumped %d items", self.table_name, len(data))

    @classmethod
    def load_dbTable_from_json(cls, dbTable_name:str, json_file_path:str):
        """ find a dbTable by name, create a new dbTable if needed
            and load the contents of the given json_file_path into the dbTable
        """
        dbTable = cls.find_dbTable_by_name(dbTable_name)
        if not dbTable:
            dbTable_config = { "TableName": dbTable_name }
            dBTable = cls.create_dbTable(dbTable_config)
            logger.info("created new dbTable with dbTable_config: %s", json.dumps(dbTable_config, indent=2) )

        original_count = cls.count_dbTable_items(dbTable)
        with open(json_file_path, 'r', encoding="utf-8") as json_file:
            data = json.load(json_file)
        load_count = len(data)
        logger.info("loading %d items from %s into dbTable:%s", load_count, json_file_path, dbTable_name)
        dbTable_batch = []
        for item in data:
            cls.add_item_to_dbTable_batch(item, dbTable_batch)
        cls.flush_dbTable_batch(dbTable_batch, dbTable)
        final_count = cls.count_dbTable_items(dbTable)
        logger.info("dbTable:%s original_count:%d loaded_count:%d final_count:%d", dbTable_name, original_count, final_count)
