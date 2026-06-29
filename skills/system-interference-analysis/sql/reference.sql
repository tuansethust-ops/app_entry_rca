SELECT process.name, SUM(sched.dur)/1e6 cpu_ms FROM sched JOIN thread USING(utid) JOIN process USING(upid) GROUP BY process.name ORDER BY cpu_ms DESC;
