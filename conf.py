class Conf:
    def __init__(self):
        self.projects = ['dubbo', 'kafka', 'skywalking', 'rocketmq', 'shardingsphere', 'hadoop', 'pulsar', 'druid',
                         'zookeeper', 'dolphinscheduler', 'cassandra', 'shenyu', 'shardingsphere-elasticjob', 'jmeter',
                         'beam', 'tomcat', 'seatunnel', 'storm']
        self.types = ['.java']
        self.data_path = "data/"
        self.repo_path = "repos/"
        self.issue_split_epoch = 200
        self.clean_split_epoch = 200
        self.config_file_suffix = [".xml", ".properties", ".json", ".yaml", ".yml", ".properties",
                                 "Configuration.java", "Config.java"]