// Generated from independent original-01 ARM fixtures.
struct Case {
  const char *action;
  unsigned count, order;
  int result;
  const char *trace;
  const char *remaining;
};
static const Case cases[] = {
    {"retrieve", 0, 0, -1, "lock;unlock", ""},
    {"retrieve", 0, 1, -1, "lock;unlock", ""},
    {"retrieve", 0, 2, -1, "lock;unlock", ""},
    {"retrieve", 1, 0, 0, "lock;unlock", ""},
    {"retrieve", 1, 1, 0, "lock;unlock", ""},
    {"retrieve", 1, 2, 0, "lock;unlock", ""},
    {"retrieve", 2, 0, 0, "lock;unlock", "1"},
    {"retrieve", 2, 1, 1, "lock;unlock", "0"},
    {"retrieve", 2, 2, 1, "lock;unlock", "0"},
    {"retrieve", 5, 0, 0, "lock;unlock", "1,2,3,4"},
    {"retrieve", 5, 1, 4, "lock;unlock", "3,2,1,0"},
    {"retrieve", 5, 2, 1, "lock;unlock", "2,3,4,0"},
    {"empty", 0, 0, 1, "", ""},
    {"empty", 0, 1, 1, "", ""},
    {"empty", 0, 2, 1, "", ""},
    {"empty", 1, 0, 0, "", "0"},
    {"empty", 1, 1, 0, "", "0"},
    {"empty", 1, 2, 0, "", "0"},
    {"empty", 2, 0, 0, "", "0,1"},
    {"empty", 2, 1, 0, "", "1,0"},
    {"empty", 2, 2, 0, "", "1,0"},
    {"empty", 5, 0, 0, "", "0,1,2,3,4"},
    {"empty", 5, 1, 0, "", "4,3,2,1,0"},
    {"empty", 5, 2, 0, "", "1,2,3,4,0"},
    {"flush", 0, 0, 0, "lock;unlock", ""},
    {"flush", 0, 1, 0, "lock;unlock", ""},
    {"flush", 0, 2, 0, "lock;unlock", ""},
    {"flush", 1, 0, 0, "lock;unlock;dtor:0;free:0;lock;unlock", ""},
    {"flush", 1, 1, 0, "lock;unlock;dtor:0;free:0;lock;unlock", ""},
    {"flush", 1, 2, 0, "lock;unlock;dtor:0;free:0;lock;unlock", ""},
    {"flush", 2, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock", ""},
    {"flush", 2, 1, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock", ""},
    {"flush", 2, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock", ""},
    {"flush", 5, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:3;free:3;lock;unlock;dtor:4;free:4;lock;unlock",
     ""},
    {"flush", 5, 1, 0,
     "lock;unlock;dtor:4;free:4;lock;unlock;dtor:3;free:3;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock",
     ""},
    {"flush", 5, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;free:2;lock;unlock;dtor:3;"
     "free:3;lock;unlock;dtor:4;free:4;lock;unlock;dtor:0;free:0;lock;unlock",
     ""},
    {"queueD1", 0, 0, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD1", 0, 1, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD1", 0, 2, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD1", 1, 0, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD1", 1, 1, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD1", 1, 2, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD1", 2, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD1", 2, 1, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD1", 2, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD1", 5, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:3;free:3;lock;unlock;dtor:4;free:4;lock;unlock;"
     "mutex_destroy",
     ""},
    {"queueD1", 5, 1, 0,
     "lock;unlock;dtor:4;free:4;lock;unlock;dtor:3;free:3;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;"
     "mutex_destroy",
     ""},
    {"queueD1", 5, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;free:2;lock;unlock;dtor:3;"
     "free:3;lock;unlock;dtor:4;free:4;lock;unlock;dtor:0;free:0;lock;unlock;"
     "mutex_destroy",
     ""},
    {"queueD2", 0, 0, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD2", 0, 1, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD2", 0, 2, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD2", 1, 0, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD2", 1, 1, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD2", 1, 2, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD2", 2, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD2", 2, 1, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD2", 2, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD2", 5, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:3;free:3;lock;unlock;dtor:4;free:4;lock;unlock;"
     "mutex_destroy",
     ""},
    {"queueD2", 5, 1, 0,
     "lock;unlock;dtor:4;free:4;lock;unlock;dtor:3;free:3;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;"
     "mutex_destroy",
     ""},
    {"queueD2", 5, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;free:2;lock;unlock;dtor:3;"
     "free:3;lock;unlock;dtor:4;free:4;lock;unlock;dtor:0;free:0;lock;unlock;"
     "mutex_destroy",
     ""},
    {"itemD1", 1, 0, 0, "", "0"},
    {"itemD0", 1, 0, 0, "free:0", "0"},
    {"retrieve", 0, 0, -1, "lock;unlock", ""},
    {"retrieve", 0, 1, -1, "lock;unlock", ""},
    {"retrieve", 0, 2, -1, "lock;unlock", ""},
    {"retrieve", 1, 0, 0, "lock;unlock", ""},
    {"retrieve", 1, 1, 0, "lock;unlock", ""},
    {"retrieve", 1, 2, 0, "lock;unlock", ""},
    {"retrieve", 2, 0, 0, "lock;unlock", "1"},
    {"retrieve", 2, 1, 1, "lock;unlock", "0"},
    {"retrieve", 2, 2, 1, "lock;unlock", "0"},
    {"retrieve", 5, 0, 0, "lock;unlock", "1,2,3,4"},
    {"retrieve", 5, 1, 4, "lock;unlock", "3,2,1,0"},
    {"retrieve", 5, 2, 1, "lock;unlock", "2,3,4,0"},
    {"empty", 0, 0, 1, "", ""},
    {"empty", 0, 1, 1, "", ""},
    {"empty", 0, 2, 1, "", ""},
    {"empty", 1, 0, 0, "", "0"},
    {"empty", 1, 1, 0, "", "0"},
    {"empty", 1, 2, 0, "", "0"},
    {"empty", 2, 0, 0, "", "0,1"},
    {"empty", 2, 1, 0, "", "1,0"},
    {"empty", 2, 2, 0, "", "1,0"},
    {"empty", 5, 0, 0, "", "0,1,2,3,4"},
    {"empty", 5, 1, 0, "", "4,3,2,1,0"},
    {"empty", 5, 2, 0, "", "1,2,3,4,0"},
    {"flush", 0, 0, 0, "lock;unlock", ""},
    {"flush", 0, 1, 0, "lock;unlock", ""},
    {"flush", 0, 2, 0, "lock;unlock", ""},
    {"flush", 1, 0, 0, "lock;unlock;dtor:0;free:0;lock;unlock", ""},
    {"flush", 1, 1, 0, "lock;unlock;dtor:0;free:0;lock;unlock", ""},
    {"flush", 1, 2, 0, "lock;unlock;dtor:0;free:0;lock;unlock", ""},
    {"flush", 2, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock", ""},
    {"flush", 2, 1, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock", ""},
    {"flush", 2, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock", ""},
    {"flush", 5, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:3;free:3;lock;unlock;dtor:4;free:4;lock;unlock",
     ""},
    {"flush", 5, 1, 0,
     "lock;unlock;dtor:4;free:4;lock;unlock;dtor:3;free:3;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock",
     ""},
    {"flush", 5, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;free:2;lock;unlock;dtor:3;"
     "free:3;lock;unlock;dtor:4;free:4;lock;unlock;dtor:0;free:0;lock;unlock",
     ""},
    {"queueD1", 0, 0, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD1", 0, 1, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD1", 0, 2, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD1", 1, 0, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD1", 1, 1, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD1", 1, 2, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD1", 2, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD1", 2, 1, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD1", 2, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD1", 5, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:3;free:3;lock;unlock;dtor:4;free:4;lock;unlock;"
     "mutex_destroy",
     ""},
    {"queueD1", 5, 1, 0,
     "lock;unlock;dtor:4;free:4;lock;unlock;dtor:3;free:3;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;"
     "mutex_destroy",
     ""},
    {"queueD1", 5, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;free:2;lock;unlock;dtor:3;"
     "free:3;lock;unlock;dtor:4;free:4;lock;unlock;dtor:0;free:0;lock;unlock;"
     "mutex_destroy",
     ""},
    {"queueD2", 0, 0, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD2", 0, 1, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD2", 0, 2, 0, "lock;unlock;mutex_destroy", ""},
    {"queueD2", 1, 0, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD2", 1, 1, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD2", 1, 2, 0, "lock;unlock;dtor:0;free:0;lock;unlock;mutex_destroy",
     ""},
    {"queueD2", 2, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD2", 2, 1, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD2", 2, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;mutex_"
     "destroy",
     ""},
    {"queueD2", 5, 0, 0,
     "lock;unlock;dtor:0;free:0;lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:3;free:3;lock;unlock;dtor:4;free:4;lock;unlock;"
     "mutex_destroy",
     ""},
    {"queueD2", 5, 1, 0,
     "lock;unlock;dtor:4;free:4;lock;unlock;dtor:3;free:3;lock;unlock;dtor:2;"
     "free:2;lock;unlock;dtor:1;free:1;lock;unlock;dtor:0;free:0;lock;unlock;"
     "mutex_destroy",
     ""},
    {"queueD2", 5, 2, 0,
     "lock;unlock;dtor:1;free:1;lock;unlock;dtor:2;free:2;lock;unlock;dtor:3;"
     "free:3;lock;unlock;dtor:4;free:4;lock;unlock;dtor:0;free:0;lock;unlock;"
     "mutex_destroy",
     ""},
    {"itemD1", 1, 0, 0, "", "0"},
    {"itemD0", 1, 0, 0, "free:0", "0"},
};
