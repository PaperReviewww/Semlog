import test8 as SB
print('Hello')
#SB.Parse_with_scrub('HPC',r'^.+? .+? .+? .+? .+? .+? (.+)$',"[,!?\\-_=]")
#SB.Parse_with_scrub('Apache',r'^.+?\] .+?\] (.+)$',"[,!?\\-_=]")
#SB.Parse_with_scrub('Zookeeper',r'^.+?\] - (.+)$',"[,!?\\-_=:]")
#SB.Parse_with_scrub('Mac',r'^.+?\]: (.+)$',"[.,!?=:]")
#SB.Parse_with_scrub('HealthApp',r'^.+\|(.+)$',"[,!?=:]")
#SB.Parse_with_scrub('Proxifier',r'^.+?\- (.+)$',"[,!?=]")
#SB.Parse_with_scrub('Android',r'^.+?: (.+)$',"[,!?\\-_=:]")
#SB.Parse_with_scrub('Linux',r'^.+?: (.+)$',"[,!?=:]")
#SB.Parse_with_scrub('Hadoop',r'^.+?\].+?: (.+)$',"[,!?=]")
#SB.Parse_with_scrub('OpenSSH',r'^.+?\]: (.+)$',"[,!?=\\-:]")
#SB.Parse_with_scrub('OpenStack',r'^.+?\] (.+)$',"[,\[\]]")
#SB.Parse_with_scrub('HDFS',r'^.+?: (.+)$',"[,!?=]")
#SB.Parse_with_scrub('Mac',r'^.+?\]: (.+)$',"[,\[\]]")
#SB.Parse_with_scrub('HDFS',r'^.+?: (.+)$',"[.,!?=:]")
#SB.Parse_with_scrub('BGL',r'^.+? .+? .+? .+? .+? .+? .+? .+? .+? (.+)$',"[.,!?=:]")
SB.Parse_with_scrub('Spark',r'^.+?: (.+)$',"[.,!?=:]")
#SB.Parse_with_scrub('Windows',r'^.+[a-z]    (.+)$',"[,]")
#SB.Parse_with_scrub('Thunderbird',r'^.+?: (.+)$',"[,\[\]]")
