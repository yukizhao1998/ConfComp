import datetime
import pytz

class Conf:
    def __init__(self):
        self.projects = ['dubbo', 'kafka', 'skywalking', 'rocketmq', 'shardingsphere', 'hadoop', 'pulsar', 'druid',
                         'zookeeper', 'dolphinscheduler', 'cassandra', 'shenyu', 'shardingsphere-elasticjob', 'jmeter',
                         'beam', 'tomcat', 'seatunnel', 'storm', 'flink', 'doris']
        self.types = ['.java']
        self.data_path = "data/"
        self.repo_path = "repos/"
        self.raw_file_name = "commit_config_related_raw"
        self.issue_split_epoch = 200
        self.clean_split_epoch = 200
        self.config_file_suffix = [".xml", ".properties", ".json", ".yaml", ".yml"]
        # self.openai_api_key = "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"
        self.openai_api_key = ""
        self.label_model = "gpt-4"
        self.dt_start = datetime.datetime(2022, 2, 1, 0, 0, 0).replace(tzinfo=pytz.timezone('UTC'))
        self.dt_end = datetime.datetime(2024, 1, 1, 0, 0, 0).replace(tzinfo=pytz.timezone('UTC'))