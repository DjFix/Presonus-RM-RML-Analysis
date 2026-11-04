#include "presonus/surface/DisplayManager.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <iostream>
struct Sink : Core::Portable::RootView {
  int n = 0, type = -1, x = 0, y = 0;
  bool onTouchInput(const Core::Portable::TouchEvent &e) override {
    ++n;
    type = e.type;
    x = e.where.x;
    y = e.where.y;
    return true;
  }
};
int main() {
  int t, i, x, y;
  while (std::cin >> t >> i >> x >> y) {
    Sink a, b;
    Presonus::DisplayManager m;
    Presonus::Panel::ControlRegistrar r;
    presonus::surface_display_port::DisplayManagerAccess::bindTouchViews(
        m, {&a, nullptr, &b});
    m.screenTouched(r, {t, i, x, y});
    Sink &s = i == 2 ? b : a;
    std::cout << a.n + b.n << ' ' << (a.n + b.n ? i : -1) << ' ' << s.type
              << ' ' << s.x << ' ' << s.y << '\n';
  }
}
