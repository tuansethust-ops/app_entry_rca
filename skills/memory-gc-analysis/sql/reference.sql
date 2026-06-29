SELECT ts,dur,name FROM slice WHERE name GLOB '*GC*' OR name GLOB '*WaitForGcToComplete*';
