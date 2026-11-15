#include "core/system/coredebug.h"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
using namespace Core::Portable;
namespace {
bool recording = false;
std::vector<std::string> calls;
void add(std::string s) {
  if (recording)
    calls.push_back(s);
}
struct Observer : ParamObserverBase {
  int changed = 0;
  void paramChanged(Parameter *, int) override { ++changed; }
};
struct Probe : NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
};
struct ComponentPort : Component {
  using Component::Component;
  void add(Probe *p) { paramList.add(p); }
};
const ParamInfo infos[] = {PARAM_INT(38, "exit", 0, 100, 0, 0, 0, 0, 0),
                           PARAM_INT(903, "touch", 0, 100, 0, 0, 0, 0, 0),
                           PARAM_INT(2, "util", 0, 100, 0, 0, 0, 0, 0)};
void rejectSend(void *, Uart_Msg_Type &) {
  throw std::logic_error("unexpected panel send");
}
void rejectMode(void *, bool) {
  throw std::logic_error("unexpected panel mode");
}
void rejectTouch(void *, Touchscreen_Type &) {
  throw std::logic_error("unexpected panel touchscreen callback");
}
struct Setup {
  Observer observer;
  ComponentPort root{"root"};
  ComponentPort *screen = new ComponentPort("mainscreen");
  Probe *exit = new Probe(infos[0]), *touch = new Probe(infos[1]),
        *util = new Probe(infos[2]);
  presonus::surface::RootServices services;
  Setup(int missing) {
    if (missing != 2)
      screen->add(exit);
    else {
      delete exit;
      exit = nullptr;
    }
    screen->add(util);
    if (missing != 3)
      root.add(touch);
    else {
      delete touch;
      touch = nullptr;
    }
    if (missing != 1)
      root.addChild(screen);
    services.children = &root;
    services.rootParameters = &root;
    services.observer = &observer;
    services.mainScreens.push_back(
        {screen,
         reinterpret_cast<Presonus::Surface::MainScreenComponent *>(
             std::uintptr_t(0x1234)),
         "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
         "_ZTIN8Presonus7Surface19MainScreenComponentE", 0x1a0434});
  }
  ~Setup() {
    if (!screen->getParent())
      delete screen;
  }
};
void row(const std::vector<int> &state) {
  std::cout << "ROW ";
  for (auto x : state)
    std::cout << x << ' ';
  std::cout << '|';
  for (const auto &s : calls)
    std::cout << s << ',';
  std::cout << '\n';
}
} // namespace
extern "C" Parameter *
__real__ZNK4Core8Portable9Component17getParameterByTagEi(const Component *,
                                                         int);
extern "C" Parameter *
__wrap__ZNK4Core8Portable9Component17getParameterByTagEi(const Component *p,
                                                         int tag) {
  add("tag" + std::to_string(tag));
  return __real__ZNK4Core8Portable9Component17getParameterByTagEi(p, tag);
}
extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  add("remove" + std::to_string(p->getTag()));
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(p,
                                                                            o);
}
extern "C" void
__real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  add("add" + std::to_string(p->getTag()));
  __real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(p, o);
}
extern "C" void __real__ZN4Core11DebugPrintfEPKcz(const char *, ...);
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *fmt, ...) {
  if (std::string(fmt).find("activeTestCount") != std::string::npos)
    add("debug");
  char buffer[2048];
  va_list a;
  va_start(a, fmt);
  std::vsnprintf(buffer, sizeof(buffer), fmt, a);
  va_end(a);
  __real__ZN4Core11DebugPrintfEPKcz("%s", buffer);
}
extern "C" void
__real__ZN8Presonus7Surface14PanelRegistrar7runTestENS1_8TestModeEb(
    Presonus::Surface::PanelRegistrar *,
    Presonus::Surface::PanelRegistrar::TestMode, bool);
extern "C" void
__wrap__ZN8Presonus7Surface14PanelRegistrar7runTestENS1_8TestModeEb(
    Presonus::Surface::PanelRegistrar *p,
    Presonus::Surface::PanelRegistrar::TestMode m, bool e) {
  add("run" + std::to_string(int(m)) + "_" + std::to_string(e));
  __real__ZN8Presonus7Surface14PanelRegistrar7runTestENS1_8TestModeEb(p, m, e);
}
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--observe-provider") {
    Observer a, b;
    Probe p(infos[2]);
    p.addObserver(&a);
    p.addObserver(&a);
    p.addObserver(&b);
    p.removeObserver(&a);
    int after = p.observers();
    p.setValue(1, false);
    p.removeObserver(&a);
    p.removeObserver(&a);
    p.removeObserver(&b);
    ComponentPort c;
    std::cout << "PROVIDER " << after << ' ' << a.changed << ' ' << b.changed
              << ' ' << p.observers() << ' '
              << (c.getParameterByTag(2) == nullptr) << '\n';
    return 0;
  }
#ifdef ROOT_UTIL
  if (argc != 3)
    return 2;
  int missing = std::atoi(argv[1]);
  Setup a(0), b(0);
  if (missing == 1) {
    a.root.removeChild(a.screen);
    b.root.removeChild(b.screen);
  }
  if (missing == 2) { // real empty screen parameter list is exercised through
                      // an actual separate child
    a.root.removeChild(a.screen);
    b.root.removeChild(b.screen);
    delete a.screen;
    delete b.screen;
    a.screen = new ComponentPort("mainscreen");
    b.screen = new ComponentPort("mainscreen");
    a.util = b.util = nullptr;
    a.root.addChild(a.screen);
    b.root.addChild(b.screen);
    a.services.mainScreens[0].component = a.screen;
    b.services.mainScreens[0].component = b.screen;
  }
  Presonus::Surface::SurfaceRootComponent roots[2];
  roots[0].bindServices(a.services);
  roots[1].bindServices(b.services);
  std::stringstream in(argv[2]);
  std::string op;
  while (std::getline(in, op, ',')) {
    calls.clear();
    recording = true;
    bool error = false;
    try {
      roots[op[0] - '0'].manageUtilPageObserver(op[1] == '+');
    } catch (const std::logic_error &) {
      error = true;
    }
    recording = false;
    row({a.util ? a.util->observers() : 0, b.util ? b.util->observers() : 0,
         int(error)});
  }
#else
  if (argc != 5)
    return 2;
  int flag = std::atoi(argv[1]), reg = std::atoi(argv[2]),
      missing = std::atoi(argv[3]), n = std::atoi(argv[4]);
  Setup s(missing);
  for (int i = 0; i < n; ++i) {
    if (s.exit)
      s.exit->addObserver(&s.observer);
    if (s.touch)
      s.touch->addObserver(&s.observer);
  }
  presonus::surface::RegistrarTestState state(
      {nullptr, rejectSend, rejectMode, rejectTouch, nullptr});
  state.touchscreen = true;
  presonus::timing::DelayTimerAccess::set(state.touchTimer, {0, 0, 0, 0, true});
  Presonus::Surface::PanelRegistrar registrar;
  registrar.bindTests(state);
  Presonus::Surface::SurfaceRootComponent root =
      reg ? Presonus::Surface::SurfaceRootComponent(registrar)
          : Presonus::Surface::SurfaceRootComponent();
  root.bindServices(s.services);
  s.services.touchscreenActive = flag;
  recording = true;
  bool error = false;
  try {
    root.terminateTestTouchscreen();
  } catch (const std::logic_error &) {
    error = true;
  }
  recording = false;
  if (!error && reg && (state.touchscreen || state.touchTimer.isExecuting()))
    return 3;
  row({int(s.services.touchscreenActive), s.exit ? s.exit->observers() : n,
       s.touch ? s.touch->observers() : n, int(error)});
#endif
}
