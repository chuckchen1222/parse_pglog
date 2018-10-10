# parse_pglog
解析，监控PGLOG

目的是可以实时从PG LOG文件中，发现日志的错误。
数据库日志配置为log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d %h


