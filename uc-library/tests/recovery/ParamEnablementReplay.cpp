#include "presonus/panel/ParamEnablementHandler.hpp"
#include <bit>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>
using Presonus::Panel::ParamEnablementHandler;
static std::vector<std::string> events;
class Probe : public Core::Portable::NumericParam {
public:
  Probe(const Core::Portable::ParamInfo &info, int id, uint32_t bits)
      : NumericParam(info), id(id), bits(bits) {}
  ~Probe() { ++destroyed; }
  float getValue() const override {
    events.push_back("g" + std::to_string(id));
    return std::bit_cast<float>(bits);
  }
  void enable(bool state) override {
    events.push_back("e" + std::to_string(id) + ":" + std::to_string(state));
    Parameter::enable(state);
  }
  int id;
  uint32_t bits;
  static inline int destroyed = 0;
};
int main() {
  int msg, nd, nt;
  uint32_t a, b, c;
  while (std::cin >> msg >> nd >> nt >> a >> b >> c) {
    Core::Portable::ParamInfo info{};
    Probe p0(info, 0, a), p1(info, 1, b), p2(info, 2, c), target(info, 3, 0);
    Probe *ps[] = {&p0, &p1, &p2};
    {
      ParamEnablementHandler h;
      for (int i = 0; i < nd; ++i)
        h.addDependency(ps[i % 3], false);
      for (int i = 0; i < nt; ++i)
        h.addTarget(&target);
      events.clear();
      if (msg == 99)
        h.changed();
      else
        h.paramChanged(&p0, msg);
      for (auto &e : events)
        std::cout << e << ' ';
      std::cout << '\n';
    }
  }
  Core::Portable::ParamInfo info{};
  Probe p(info, 0, 0x3f800000), t(info, 3, 0);
  { // Observation disabled still stores the dependency, without registration.
    ParamEnablementHandler h;
    events.clear();
    h.addTarget(&t);
    h.addDependency(&p, false);
    assert(events.empty());
    p.changed();
    assert(events.empty());
    h.changed();
    assert(events == std::vector<std::string>({"g0", "e3:1"}));
  }
  int before = Probe::destroyed;
  {
    ParamEnablementHandler h;
    h.addTarget(&t);
    h.addTarget(&t);
    h.addDependency(&p, true);
    h.addDependency(&p, true);
    h.addDependency(&p, false);
    events.clear();
    p.changed();
    assert(events.size() ==
           10); // Two notifications, 3 reads and 2 enables each.
    events.clear();
    p.rangeChanged();
    assert(events.empty());
  }
  assert(Probe::destroyed == before);
  events.clear();
  p.changed();
  assert(events.empty());
  std::cerr << "provider duplicate notification, detach and borrowed lifetime "
               "passed\n";
}
