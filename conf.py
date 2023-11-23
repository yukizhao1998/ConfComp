class Conf:
    def __init__(self):
        self.projects = ['ZOOKEEPER', 'ZEPPELIN', 'MAPREDUCE', 'HDFS', 'HBASE', 'HIVE', 'GROOVY', 'CAMEL', 'CASSANDRA',
                         'FLINK', 'IGNITE', 'KAFKA', 'SPARK']
        self.years = ['2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023']
        self.types = ['.java']
        self.data_path = "data/"
        self.repo_path = "repos/"
        self.proj_repo = {'MESOS': ['apache/mesos'], 'AMQ': ['apache/activemq'], 'HBASE': ['apache/hbase'],
                          'SPARK': ['apache/spark'], 'KAFKA': ['apache/kafka'], 'GROOVY': ['apache/groovy'],
                          'ZEPPELIN': ['apache/zeppelin'], 'HDFS': ['apache/hadoop-hdfs', 'apache/hadoop'],
                          'FLINK': ['apache/flink'], 'ROCKETMQ': ['apache/rocketmq'], 'CAMEL': ['apache/camel'],
                          'MAPREDUCE': ['apache/hadoop-mapreduce', 'apache/hadoop'], 'IGNITE': ['apache/ignite'],
                          'CASSANDRA': ['apache/cassandra'], 'HIVE': ['apache/hive'], 'ZOOKEEPER': ['apache/zookeeper']}
        self.issue_split_epoch = 200