from __future__ import annotations
import collections, re
from typing import Dict, Iterable, List, Optional, Pattern, Tuple
from .models import Event, Slice, StateInterval

LINE_RE = re.compile(
    r'^\s*(?P<comm>.+?)-(?P<tid>\d+)\s+' 
    r'(?:\(\s*(?P<tgid>\d+|-+)\)\s+)?'
    r'\[(?P<cpu>\d+)\]\s+\S+\s+'
    r'(?P<ts>\d+\.\d+):\s+(?P<event>[^:]+):\s*(?P<details>.*)$')
SWITCH_RE = re.compile(
    r'prev_comm=(.*?) prev_pid=(\d+) prev_prio=(\d+) prev_state=(\S+) '
    r'==> next_comm=(.*?) next_pid=(\d+) next_prio=(\d+)')
WAKE_RE = re.compile(r'(?:comm=(.*?)\s+)?pid=(\d+)\s+prio=(\d+)\s+target_cpu=(\d+)')
BLOCKED_RE = re.compile(r'pid=(\d+)\s+iowait=(\d+)\s+caller=(\S+)')
EVENT_TIME_RE = re.compile(r'eventTimeNano=(\d+)')

class Systrace:
    backend_name = "systrace_text"

    def __init__(self, text: str, source_path: str = '') -> None:
        self.source_path=source_path
        self.events: List[Event]=[]
        self.slices: List[Slice]=[]
        self.async_slices: List[Slice]=[]
        self.states: Dict[int,List[StateInterval]]=collections.defaultdict(list)
        self.running: List[StateInterval]=[]
        self.thread_meta: Dict[int,Tuple[str,int]]={}
        self.blocked_reasons: Dict[int,List[Tuple[float,int,str]]]=collections.defaultdict(list)
        self.trace_start: Optional[float]=None
        self.trace_end: Optional[float]=None
        self._parse(text)

    @staticmethod
    def _state_name(prev_state: str) -> str:
        if prev_state.startswith('R'): return 'Runnable'
        if prev_state.startswith('D'): return 'D'
        if prev_state.startswith('S'): return 'Sleeping'
        if prev_state.startswith('I'): return 'Idle'
        return prev_state

    def _parse(self,text: str) -> None:
        stacks=collections.defaultdict(list)
        async_open: Dict[Tuple[str,str],Tuple[float,int,int,str,int,str]]={}
        current: Dict[int,Tuple[str,float,Optional[int]]]={}
        last_ts=None

        def close(tid: int, ts: float) -> None:
            old=current.get(tid)
            if not old: return
            state,start,cpu=old
            if ts <= start: return
            it=StateInterval(start,ts,state,tid,cpu)
            self.states[tid].append(it)
            if state=='Running': self.running.append(it)

        for line in text.splitlines():
            m=LINE_RE.match(line)
            if not m: continue
            g=m.groupdict()
            ts=float(g['ts']); tid=int(g['tid']); cpu=int(g['cpu'])
            tgid=int(g['tgid']) if g.get('tgid') and g['tgid'].isdigit() else tid
            ev=Event(ts,g['event'].strip(),g['details'],tid,tgid,g['comm'].strip(),cpu)
            self.events.append(ev); self.thread_meta[tid]=(ev.comm,tgid)
            self.trace_start=ts if self.trace_start is None else min(self.trace_start,ts)
            self.trace_end=ts if self.trace_end is None else max(self.trace_end,ts)
            last_ts=ts
            if ev.event=='tracing_mark_write':
                det=ev.details
                parts=det.split('|')
                typ=parts[0] if parts else ''
                if typ=='B' and len(parts)>=3:
                    name='|'.join(parts[2:])
                    stacks[tid].append((ts,name,tid,tgid,ev.comm,cpu))
                elif typ=='E' or det=='E':
                    if stacks[tid]:
                        st,name,ti,tg,comm,c0=stacks[tid].pop()
                        self.slices.append(Slice(st,ts,name,ti,tg,comm,c0,False))
                elif typ=='S' and len(parts)>=4:
                    # S|pid|name|cookie
                    pid_key=parts[1]; cookie=parts[-1]; name='|'.join(parts[2:-1])
                    async_open[(pid_key,name,cookie)]=(ts,tid,tgid,ev.comm,cpu,name)
                elif typ=='F' and len(parts)>=3:
                    pid_key=parts[1]; cookie=parts[-1]
                    name='|'.join(parts[2:-1]) if len(parts)>=4 else ''
                    key=(pid_key,name,cookie)
                    if key in async_open:
                        st,ti,tg,comm,c0,name=async_open.pop(key)
                        sl=Slice(st,ts,name,ti,tg,comm,c0,True)
                        self.async_slices.append(sl); self.slices.append(sl)
            elif ev.event=='sched_switch':
                sm=SWITCH_RE.match(ev.details)
                if sm:
                    _pc,ppid,_pp,pstate,_nc,npid,_np=sm.groups()
                    ppid=int(ppid); npid=int(npid)
                    close(ppid,ts); current[ppid]=(self._state_name(pstate),ts,cpu)
                    close(npid,ts); current[npid]=('Running',ts,cpu)
            elif ev.event in ('sched_wakeup','sched_waking'):
                wm=WAKE_RE.search(ev.details)
                if wm:
                    pid=int(wm.group(2))
                    if pid not in current or current[pid][0] not in ('Running','Runnable'):
                        close(pid,ts); current[pid]=('Runnable',ts,int(wm.group(4)))
            elif ev.event=='sched_blocked_reason':
                bm=BLOCKED_RE.search(ev.details)
                if bm:
                    self.blocked_reasons[int(bm.group(1))].append((ts,int(bm.group(2)),bm.group(3)))
        if last_ts is not None:
            for tid in list(current): close(tid,last_ts)
        self.slices.sort(key=lambda x:(x.ts,x.end))
        self.running.sort(key=lambda x:(x.start,x.end))

    @staticmethod
    def _rx(pattern: str | Pattern[str] | None) -> Optional[Pattern[str]]:
        if pattern is None: return None
        return pattern if hasattr(pattern,'search') else re.compile(pattern,re.I)

    def find_slices(self, pattern: str | Pattern[str] | None=None, *, tgid: int | None=None,
                    tid: int | None=None, start: float | None=None, end: float | None=None) -> List[Slice]:
        rx=self._rx(pattern); out=[]
        for s in self.slices:
            if rx and not rx.search(s.name): continue
            if tgid is not None and s.tgid!=tgid: continue
            if tid is not None and s.tid!=tid: continue
            if start is not None and s.end<=start: continue
            if end is not None and s.ts>=end: continue
            out.append(s)
        return out

    def longest(self, pattern: str, **kw) -> Optional[Slice]:
        xs=self.find_slices(pattern,**kw)
        return max(xs,key=lambda x:x.dur,default=None)

    def first(self, pattern: str, **kw) -> Optional[Slice]:
        xs=self.find_slices(pattern,**kw)
        return min(xs,key=lambda x:x.ts,default=None)

    def sum_slice_ms(self, pattern: str, **kw) -> float:
        return sum(x.dur_ms for x in self.find_slices(pattern,**kw))

    def state_ms(self, tid: int, start: float, end: float) -> Dict[str,float]:
        c=collections.Counter()
        for i in self.states.get(tid,[]):
            ov=max(0.0,min(i.end,end)-max(i.start,start))
            if ov: c[i.state]+=ov*1000.0
        return dict(c)

    def state_ms_for_process(self,tgid:int,start:float,end:float) -> Dict[str,float]:
        c=collections.Counter()
        tids=[tid for tid,(_c,tg) in self.thread_meta.items() if tg==tgid]
        for tid in tids:
            c.update(self.state_ms(tid,start,end))
        return dict(c)

    def blocked_reason_near(self,tid:int,start:float,end:float) -> List[Tuple[float,int,str]]:
        return [x for x in self.blocked_reasons.get(tid,[]) if start-0.002<=x[0]<=end+0.002]

    def event_time_latency_ms(self, tgid:int, start:float,end:float) -> Optional[float]:
        for e in self.events:
            if e.tgid!=tgid or not(start<=e.ts<=end): continue
            if e.event!='tracing_mark_write': continue
            if 'deliverInputEvent' not in e.details and 'dispatchInputEvent MotionEvent DOWN' not in e.details: continue
            m=EVENT_TIME_RE.search(e.details)
            if m:
                return (e.ts-int(m.group(1))/1e9)*1000.0
        return None

    def sum_paired_event_ms(self, begin_event: str, end_event: str, *, tgid: int | None=None, tid: int | None=None, start: float | None=None, end: float | None=None) -> float:
        """Pair begin/end kernel events per TID and sum durations in the window."""
        stacks=collections.defaultdict(list); total=0.0
        for e in self.events:
            if start is not None and e.ts < start: continue
            if end is not None and e.ts > end: continue
            if tgid is not None and e.tgid != tgid: continue
            if tid is not None and e.tid != tid: continue
            if e.event == begin_event:
                stacks[e.tid].append(e.ts)
            elif e.event == end_event and stacks[e.tid]:
                st=stacks[e.tid].pop()
                if e.ts > st: total += (e.ts-st)*1000.0
        return total


    def event_count(self, event_name: str) -> int:
        return sum(1 for e in self.events if e.event == event_name)

    def has_event(self, event_name: str) -> bool:
        return any(e.event == event_name for e in self.events)

    def tids_for_process(self, tgid: int) -> List[int]:
        return [tid for tid, (_comm, group) in self.thread_meta.items() if group == tgid]

    def intervals(self, tid: int, state: str, start: float, end: float) -> List[StateInterval]:
        out=[]
        for item in self.states.get(tid, []):
            if item.state != state or item.end <= start or item.start >= end:
                continue
            out.append(StateInterval(max(start,item.start), min(end,item.end), item.state, item.tid, item.cpu))
        return out

    def process_intervals(self, tgid: int, state: str, start: float, end: float) -> List[StateInterval]:
        out=[]
        for tid in self.tids_for_process(tgid):
            out.extend(self.intervals(tid,state,start,end))
        return sorted(out,key=lambda x:(x.start,x.end,x.tid))

    def nested_slices(self, parent: Slice, pattern: str | Pattern[str] | None = None) -> List[Slice]:
        return [s for s in self.find_slices(pattern,tid=parent.tid,start=parent.ts,end=parent.end)
                if s.ts >= parent.ts and s.end <= parent.end and s is not parent]

    def sum_interval_overlap_ms(self, left: Iterable[StateInterval], right: Iterable[StateInterval]) -> float:
        total=0.0
        a=sorted(left,key=lambda x:x.start); b=sorted(right,key=lambda x:x.start)
        i=j=0
        while i < len(a) and j < len(b):
            total += max(0.0,min(a[i].end,b[j].end)-max(a[i].start,b[j].start))*1000.0
            if a[i].end <= b[j].end: i+=1
            else: j+=1
        return total

    def same_cpu_interval_overlap_ms(self, left: Iterable[StateInterval], right: Iterable[StateInterval]) -> float:
        total=0.0
        for a in left:
            for b in right:
                if a.cpu is not None and b.cpu is not None and a.cpu != b.cpu:
                    continue
                total += max(0.0,min(a.end,b.end)-max(a.start,b.start))*1000.0
        return total

    def find_events(self, names: Iterable[str], *, start: float | None=None, end: float | None=None, tgid: int | None=None) -> List[Event]:
        wanted=set(names); out=[]
        for event in self.events:
            if event.event not in wanted: continue
            if start is not None and event.ts < start: continue
            if end is not None and event.ts >= end: continue
            if tgid is not None and event.tgid != tgid: continue
            out.append(event)
        return out

    def close(self) -> None:
        return None

    def summary_counts(self) -> Dict[str, int]:
        return {
            "slice_count": len(self.slices),
            "thread_state_count": sum(len(items) for items in self.states.values()),
            "sched_slice_count": len(self.running),
            "process_count": len({tgid for _tid, (_comm, tgid) in self.thread_meta.items()}),
            "thread_count": len(self.thread_meta),
            "event_count": len(self.events),
        }

    def capabilities(self) -> Dict[str,bool]:
        events={e.event for e in self.events}
        names='\n'.join(s.name for s in self.slices)
        return {
            'backend_perfetto_sql': False,
            'sched': 'sched_switch' in events,
            'wakeup': bool({'sched_wakeup','sched_waking'} & events),
            'blocked_reason': 'sched_blocked_reason' in events,
            'direct_reclaim': 'mm_vmscan_direct_reclaim_begin' in events,
            'page_fault': any(x in events for x in ('mm_filemap_fault','filemap_fault','exceptions_page_fault_user')),
            'block_io': any(x.startswith('block_') for x in events),
            'cpu_frequency': 'cpu_frequency' in events or 'clock_set_rate' in events,
            'binder_slices': 'AIDL::' in names or 'binder' in names.lower(),
            'gc_slices': bool(re.search(r'WaitForGcToComplete|concurrent mark compact GC|CollectorTransition|\bGC\b',names,re.I)),
            'render_slices': bool(re.search(r'DrawFrames|Vulkan finish frame|Texture upload|dequeueBuffer',names,re.I)),
            'art_slices': bool(re.search(r'OpenDexFilesFromOat|GetBestInfo|GetStatus|LoadedArsc|LoadApkAssets',names,re.I)),
            'binder_transactions': False,
            'frame_timeline': False,
            'android_startups': False,
            'counters': 'tracing_mark_write' in events or 'counter' in events,
        }

    def running_occupants(self, intervals: Iterable[StateInterval], cpus=(), exclude_tids=()) -> Dict[str,float]:
        out=collections.Counter(); ex=set(exclude_tids)
        windows=list(intervals)
        for run in self.running:
            if run.tid in ex or (cpus and run.cpu not in cpus): continue
            ov=0.0
            for w in windows:
                ov += max(0.0,min(run.end,w.end)-max(run.start,w.start))
            if ov:
                comm=self.thread_meta.get(run.tid,(f'tid:{run.tid}',run.tid))[0]
                if run.tid == 0 or comm in ('<idle>', 'swapper') or comm.startswith('swapper/'):
                    continue
                out[comm]+=ov*1000.0
        return dict(out)
