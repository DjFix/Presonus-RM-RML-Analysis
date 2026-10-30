#include "presonus/application/ApplicationManagers.hpp"
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>

using namespace presonus::startup;
struct Case {
  std::string op, home, name, expectedEvents;
  int argc, app, mode, result, mask, releaseMask, mutargc, singleton;
  int homePresent, namePresent, expectedResult, expectedArgc, expectedArgv,
      expectedApp, expectedSingleton;
};
struct RecordingBindings final : Bindings {
  State &state;
  const Case &c;
  std::vector<std::string> events;
  static inline int app, other;
  RecordingBindings(State &s, const Case &c) : state(s), c(c) {}
  static void *pointer(int n) {
    return n == 0 ? nullptr : n == 1 ? &app : &other;
  }
  static int id(void *p) {
    return p == nullptr ? 0 : p == &app ? 1 : p == &other ? 2 : -1;
  }
  void mutate(int mask) {
    if (mask & 1)
      state.app = &other;
    if (mask & 2)
      state.app = nullptr;
    if (mask & 4)
      state.argc = c.mutargc;
  }
  int event(const char *name, void *p, bool release = false) {
    events.emplace_back(std::string(name) + ":" + std::to_string(id(p)));
    mutate(release ? c.releaseMask : c.mask);
    return c.result;
  }
  const char *homeDirectory() override {
    return c.homePresent ? c.home.c_str() : nullptr;
  }
  void readDeviceName(Core::CStringBuffer<64> &name,
                      const Core::ConstString &key,
                      const Core::ConstString &path) override {
    if (!(key == "DEVICE_NAME"))
      std::abort();
    events.emplace_back(std::string("path:") + path.str());
    if (c.namePresent)
      name = c.name.c_str();
  }
  void starting(const char *s) override {
    events.emplace_back(std::string("starting:") + s);
  }
  void unrecognized(const char *s) override {
    events.emplace_back(std::string("unknown:") + s);
  }
  void *construct(Kind kind, int mode) override {
    static const char *names[] = {
        "SurfaceApplication", "StormApplication",     "RogueApplication",
        "BeastApplication",   "WolverineApplication", "WolverineRMLApplication",
        "GambitApplication",  "GambitRMLApplication"};
    events.emplace_back(std::string("construct:") +
                        names[static_cast<int>(kind)] + ":" +
                        std::to_string(mode));
    mutate(c.mask);
    return &app;
  }
  int init(void *p) override { return event("init", p); }
  int run(void *p) override { return event("run", p); }
  int idle(void *p) override { return event("idle", p); }
  int shutdown(void *p) override { return event("shutdown", p); }
  int runTests(void *p, int mode, int argc, char **argv) override {
    if (mode != c.mode || argc != state.argc || argv != state.argv)
      std::abort();
    return event("tests", p);
  }
  void release(void *p, Role) override { event("release", p, true); }
};
template <class T> struct SingletonAccess : T {
  static void set(T *p) { T::theInstance = p; }
  static T *get() { return T::theInstance; }
};
template <class T> int call(T &m, const Case &c) {
  using Mode =
      std::conditional_t<std::is_same_v<T, Presonus::OmapApplicationManager>,
                         Presonus::AppMode, int>;
  if (c.op == "L") {
    m.setCommandLine(c.mode, m.engine.state.argv);
    return 0;
  }
  if (c.op == "I")
    return m.idle();
  if (c.op == "N")
    return m.initTheApp();
  if (c.op == "S")
    return m.shutdown();
  if (c.op == "T")
    return m.runTests(static_cast<Mode>(c.mode));
  if (c.op == "U")
    return m.startup(static_cast<Mode>(c.mode));
  if (c.op == "R")
    return m.restart();
  std::abort();
}
template <class T> void replay(const Case &c, std::size_t index) {
  T *m = new T;
  auto *other = reinterpret_cast<T *>(&RecordingBindings::other);
  char *argv[1] = {nullptr};
  m->engine.state = {c.argc, argv, RecordingBindings::pointer(c.app)};
  RecordingBindings bindings(m->engine.state, c);
  m->engine.bind(bindings);
  SingletonAccess<T>::set(c.singleton == 0   ? nullptr
                          : c.singleton == 1 ? m
                                             : other);
  State resultState;
  int result = 0;
  bool deleted = false;
  if (c.op == "C1" || c.op == "C2") {
    // Both compiler constructor variants share the source constructor. Original
    // ranges are checked independently; this is source behavior, no ARM layout.
    m->~T();
    SingletonAccess<T>::set(c.singleton == 0   ? nullptr
                            : c.singleton == 1 ? m
                                               : other);
    new (m) T;
    resultState = m->engine.state;
  } else if (c.op == "D0" || c.op == "D1") {
    resultState = m->engine.state;
    if (c.op == "D0") {
      delete m;
      deleted = true;
      bindings.events.emplace_back("manager-delete");
    } else {
      m->~T();
      deleted = true;
      ::operator delete(m);
    }
  } else {
    result = call(*m, c);
    resultState = m->engine.state;
  }
  int singleton = SingletonAccess<T>::get() == nullptr ? 0
                  : SingletonAccess<T>::get() == m     ? 1
                                                       : 2;
  std::string events;
  for (const auto &e : bindings.events) {
    if (!events.empty())
      events += "|";
    events += e;
  }
  bool pass = result == c.expectedResult &&
              resultState.argc == c.expectedArgc &&
              bool(resultState.argv) == bool(c.expectedArgv) &&
              RecordingBindings::id(resultState.app) == c.expectedApp &&
              singleton == c.expectedSingleton && events == c.expectedEvents;
  // The recorder holds a state reference which is never accessed after delete.
  SingletonAccess<T>::set(nullptr);
  if (!deleted)
    delete m;
  if (!pass) {
    std::cerr << "case " << index << " " << c.op << " got " << result << ","
              << resultState.argc << "," << bool(resultState.argv) << ","
              << RecordingBindings::id(resultState.app) << "," << singleton
              << " events=" << events << " expected=" << c.expectedEvents
              << '\n';
    std::exit(1);
  }
}
int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  std::ifstream input(argv[1]);
  std::string line;
  std::size_t count = 0;
  while (std::getline(input, line)) {
    Case c;
    std::istringstream s(line);
    s >> c.op >> c.argc >> c.app >> c.mode >> c.result >> c.mask >>
        c.releaseMask >> c.mutargc >> c.singleton >> c.homePresent >>
        c.namePresent >> std::quoted(c.home) >> std::quoted(c.name) >>
        c.expectedResult >> c.expectedArgc >> c.expectedArgv >> c.expectedApp >>
        c.expectedSingleton >> std::quoted(c.expectedEvents);
    if (!s)
      return 3;
    if (std::string(argv[2]) == "client")
      replay<Presonus::OmapApplicationManager>(c, count);
    else
      replay<Presonus::Mixer::MixerManager>(c, count);
    ++count;
  }
  if (!count)
    return 4;
  std::cout << "passed " << count << " original manager cases\n";
}
