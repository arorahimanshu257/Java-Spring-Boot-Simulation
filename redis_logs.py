import os
from typing import Optional
from redis.client import Redis
import json

from PipelineModel.PipelineLogs.RuntimeLogs import RuntimeLogs

from helpers.logger_config import logger

from helpers.pg_client import postgres_client

logger.info('Logs is starting up')

class PipelineAILogs:

    progress: str = "STARTED"
    executionId: Optional[str] = None
    pipelineId: Optional[int] = None
    sender: Optional[str] = None

    def push_logs_to_database(self,execution_id, logs_json):

        connection = postgres_client.get_connection()

        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO dadb.da_workflow_execution_logs (executionid, logs) VALUES (%s, %s)"
                cursor.execute(sql, (execution_id, logs_json))
            connection.commit()
            logger.info(f"Logs for execution ID {execution_id} successfully pushed to the database.")
        except Exception as e:
            connection.rollback()
            logger.error(f"Error pushing logs to database: {str(e)}")
        
        finally:
            postgres_client.release_connection(conn=connection)
            logger.info("Released connection")

    def publishLogs(self, logs: str,color: Optional[str] = None, redisClient:Redis = None ):
        logStream = os.getenv('ENABLE_LOGSTREAMING')
        persistent_logging = os.getenv("PERSISTENT_LOGGING")

        self.progress = "IN PROGRESS"
        if "DA Pipeline Logs Completed" in logs or "DA Pipeline Exception:" in logs:
            self.progress = "FINISHED"
        elif color is not None and color == "red":
            self.progress = "EXCEPTION"

        if logStream == 'True':
            
            log_entry = RuntimeLogs(
            pipelineId=self.pipelineId,
            progress=self.progress,
            content=logs,
            color=color,
            sender=self.sender,
            executionId=self.executionId
            )

            log_entry_json = json.dumps(log_entry.model_dump(), indent=2, ensure_ascii=False)

            logger.info('---------------- Redis Publisher ---------------- ')
            logger.info("Execution Id is ---------------- %s", self.executionId)
            logger.info("Pipeline Id is ---------------- %s", self.pipelineId)
            logger.info("Color is ---------------- %s", color)
            logger.info("Content is ---------------- %s", logs)

            try:
    
                redisClient.publish(self.executionId, log_entry_json)

                logger.info('--------------Published the topic------------ %s', log_entry_json)

            except Exception as e:

                logger.error(f"Could not connect to Redis:{e}")

                raise Exception(f"Could not connect to Redis:{e}")
            
        if persistent_logging == 'True':

            log_entry = RuntimeLogs(
            pipelineId=self.pipelineId,
            progress=self.progress,
            content=logs,
            color=color,
            sender=self.sender,
            executionId=self.executionId
            )

            log_entry_json = json.dumps(log_entry.model_dump(), indent=2, ensure_ascii=False)
            
            try:
    
                self.push_logs_to_database(self.executionId, log_entry_json)

                logger.info('--------------Published the topic------------ %s', log_entry_json)

            except Exception as e:

                logger.error(f"Could not connect to PostGres:{e}")

                raise Exception(f"Could not connect to PostGres:{e}")
