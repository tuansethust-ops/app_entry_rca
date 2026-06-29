SELECT utid, SUM(dur)/1e6 AS running_ms FROM sched GROUP BY utid;
