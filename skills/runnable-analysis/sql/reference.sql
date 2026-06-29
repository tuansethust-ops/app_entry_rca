SELECT utid, SUM(dur)/1e6 AS runnable_ms FROM thread_state WHERE state='R' GROUP BY utid;
