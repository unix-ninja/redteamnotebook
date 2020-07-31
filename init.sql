CREATE TABLE node_graph (
  nodeid TEXT,
  parentid TEXT,
  basename TEXT,
  icon TEXT,
  mtime FLOAT,
  UNIQUE(nodeid)
);

CREATE TABLE notes (
  nodeid TEXT,
  content TEXT,
  mtime FLOAT,
  UNIQUE(nodeid) ON CONFLICT REPLACE
);
