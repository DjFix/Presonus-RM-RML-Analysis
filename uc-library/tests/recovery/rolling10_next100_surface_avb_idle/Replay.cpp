#include "presonus/avb/AvbComponent.hpp"
#include "presonus/avb/SurfaceAvbComponent.hpp"
#include "presonus/dice/packet_services.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>
extern "C" std::int64_t
realClock() asm("__real__ZN8presonus4dice19packetClockRawTicksEv");
namespace {
std::int64_t ticks = 0;
int clockCalls = 0;
} // namespace
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  ++clockCalls;
  return ticks;
}

struct Child : Core::Portable::Component {
  int &calls;
  explicit Child(int &calls) : calls(calls) {}
  void onIdle() override { ++calls; }
};
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--clock") {
    const auto a = realClock(), b = realClock();
    assert(a >= 0 && b >= a);
    std::cout << a << ' ' << b << '\n';
    return 0;
  }
  using Access = presonus::avb::SurfaceAvbIdleMaintenanceAccess;
  using Other = presonus::avb::AvbIdleMaintenanceAccess;
  assert(Access::get() == 0 && Other::get() == 0);
  std::int64_t last, raw;
  int receiver;
  while (std::cin >> last >> raw >> receiver) {
    Access::set(last);
    Other::set(0x12345678);
    ticks = raw;
    clockCalls = 0;
    int childCalls = 0;
    std::int64_t after = 0;
    {
      Presonus::AVB::SurfaceAvbComponent a, b;
      a.addChild(new Child(childCalls));
      b.addChild(new Child(childCalls));
      if (receiver)
        b.onIdle();
      else
        a.onIdle();
      after = Access::get();
      assert(clockCalls == 1 && childCalls == 0 && Other::get() == 0x12345678);
    }
    assert(Access::get() == after && Other::get() == 0x12345678);
    std::cout << after << ' ' << clockCalls << ' ' << childCalls << '\n';
  }
}
