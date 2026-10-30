#include "presonus/surface/DisplayManager.hpp"
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using Root = Core::Portable::RootView;
static bool running = false, callback = false;
static std::vector<std::string> trace;
extern "C" bool
__real__ZN4Core8Portable12RootViewBase6redrawEv(Core::Portable::RootViewBase *);
extern "C" bool __wrap__ZN4Core8Portable12RootViewBase6redrawEv(
    Core::Portable::RootViewBase *r) {
  if (running)
    trace.push_back(callback ? "callback-redraw" : "redraw");
  return __real__ZN4Core8Portable12RootViewBase6redrawEv(r);
}
extern "C" void __wrap__ZN4Core8Platform13CurrentThread5sleepEj(unsigned ms) {
  if (!running || ms != 1)
    throw std::runtime_error("unexpected sleep");
  trace.push_back("sleep:1");
}
class CapturePort final : public Presonus::IDisplayPort {
public:
  Root &root;
  const void *active;
  const void *next;
  int waits;
  bool clear, cleared = false;
  CapturePort(Root &r, int n, bool c)
      : root(r), active(r.accessForRead()->scan0),
        next(r.getNextRenderBuffer()), waits(n), clear(c) {}
  int label(const void *p) const {
    return p == active ? 0 : p == next ? 1 : -1;
  }
  bool isDisplayBufferActive(const void *p) override {
    if (p != root.getNextRenderBuffer())
      throw std::runtime_error("real next buffer mismatch");
    trace.push_back("active:" + std::to_string(label(p)));
    if (waits > 0) {
      --waits;
      if (clear && !cleared) {
        cleared = true;
        callback = true;
        root.redraw();
        callback = false;
      }
      return true;
    }
    return false;
  }
  int updateDisplay(Presonus::DisplayUpdate &u) override {
    if (u.display != 0 || u.data != root.accessForRead())
      throw std::runtime_error("actual descriptor identity");
    std::ostringstream text;
    text << "update:" << int(u.display) << ":" << u.x << "," << u.y << ","
         << u.width << "," << u.height << ":" << label(u.data->scan0);
    trace.push_back(text.str());
    return -17;
  }
  int sendDisplayCommands(unsigned char, const Presonus::DisplayCommand *,
                          int) override {
    std::abort();
  }
};
static void printRects(const Root &root) {
  const auto &v = root.getDirtyRegion().getRects();
  std::cout << "[";
  for (int i = 0; i < v.count(); ++i) {
    if (i)
      std::cout << ",";
    const auto &r = v[i];
    std::cout << "[" << r.left << "," << r.top << "," << r.right << ","
              << r.bottom << "]";
  }
  std::cout << "]";
}
int main() {
  for (int i = 0; i < 24; ++i) {
    int width = i % 6 >= 4 ? 70000 : 8, height = i % 6 >= 4 ? 3 : 8;
    auto mode = i % 2 ? Core::Portable::RootViewBase::kFlipMode
                      : Core::Portable::RootViewBase::kOffscreenMode;
    Root root(Core::Rect(0, 0, width, height), Core::kBitmapRGBAlpha, mode);
    root.redraw();
    if (i % 6 != 1) {
      if (i % 6 == 4)
        root.invalidate(Core::Rect(40000, 0, 60000, 2));
      else if (i % 6 == 5)
        root.invalidate(Core::Rect(65535, 0, 69999, 2));
      else if (i % 6 == 2) {
        root.invalidate(Core::Rect(0, 0, 2, 2));
        root.invalidate(Core::Rect(5, 5, 8, 8));
      } else
        root.invalidate(Core::Rect(1, 1, 6, 5));
    }
    bool suspended = i % 7 == 0;
    int waits = i % 3;
    bool clear = i % 5 == 3;
    CapturePort port(root, waits, clear);
    Presonus::DisplayManager manager;
    presonus::surface_display_port::DisplayManagerAccess::bind(manager, root,
                                                               port, suspended);
    std::cout << "{\"index\":" << i << ",\"mode\":" << int(mode)
              << ",\"width\":" << width << ",\"height\":" << height
              << ",\"suspended\":" << int(suspended) << ",\"waits\":" << waits
              << ",\"clear\":" << int(clear) << ",\"dirty\":";
    printRects(root);
    trace.clear();
    running = true;
    manager.flushColorLcdUpdates();
    running = false;
    std::cout << ",\"dirty_after\":";
    printRects(root);
    std::cout << ",\"trace\":[";
    for (unsigned n = 0; n < trace.size(); ++n) {
      if (n)
        std::cout << ",";
      std::cout << "\"" << trace[n] << "\"";
    }
    std::cout << "]}\n";
  }
}
