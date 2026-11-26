#include "presonus/DAWChannel.hpp"
#include "presonus/DAWChannelGroup.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <vector>
using Core::Portable::Component;
using Core::Portable::ParamInfo;
class Foreign : public Component {};
static std::vector<Component *> roster;
static std::vector<int> calls;
extern "C" void __real__ZN4Core8Portable9Component6onIdleEv(Component *);
extern "C" void __wrap__ZN4Core8Portable9Component6onIdleEv(Component *self) {
  for (unsigned i = 0; i < roster.size(); ++i)
    if (roster[i] == self)
      calls.push_back(i);
  __real__ZN4Core8Portable9Component6onIdleEv(self);
}
int main(int argc, char **argv) {
  assert(argc == 3);
  int value = std::atoi(argv[1]), count = std::atoi(argv[2]);
  static const ParamInfo used =
      PARAM_FLOAT(0, "used", -20, 20, 0, 0, nullptr, nullptr, 0, 0);
  Presonus::DAWChannelGroup group;
  group.addParameters(&used, 1, false);
  group.getParameterByTag(0)->setValue(value, false);
  for (int i = 0; i < count; ++i) {
    Component *child = i % 2
                           ? static_cast<Component *>(new Presonus::DAWChannel)
                           : new Foreign;
    roster.push_back(child);
    group.addChild(child);
  }
  group.init(false);
  group.onIdle();
  std::cout << "used " << group.getUsedCount() << "\nidle ";
  for (unsigned i = 0; i < calls.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << calls[i];
  }
  std::cout << '\n';
}
