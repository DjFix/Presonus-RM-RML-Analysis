#include "presonus/mixer/OutputComponent.hpp"
#include <iostream>

int main() {
  int target, tag, message, section, initial, dirty, mutate;
  while (std::cin >> target >> tag >> message >> section >> initial >> dirty >>
         mutate) {
    presonus::mixer::ChannelState channel;
    presonus::output_port::Bindings b{channel};
    b.outputCoeffChanged = b.sectionOneCoeffChanged = initial;
    b.updatePending = dirty;
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kInt;
    info.tag = tag;
    Core::Portable::NumericParam parameter(info);
    int calls = 0, observedArgument = 0, observedDirty = -1;
    int observedOutput = -1, observedSection = -1;
    auto capture = [&](int argument) {
      ++calls;
      observedArgument = argument;
      observedDirty = b.updatePending;
      observedOutput = b.outputCoeffChanged;
      observedSection = b.sectionOneCoeffChanged;
      if (mutate) {
        info.tag = tag == 14 ? 400 : 14;
        b.outputCoeffChanged = b.sectionOneCoeffChanged = 9;
        b.updatePending = false;
      }
    };
    b.channelParamChanged = [&](Core::Portable::Parameter *p, int value) {
      if (p != &parameter)
        throw 1;
      capture(value);
    };
    b.channelSectionCoeffChanged = capture;
    Presonus::Mixer::OutputComponent component(b);
    if (target == 5)
      component.paramChanged(&parameter, message);
    else if (target == 23)
      component.setSectionCoeffChanged(section);
    else
      return 2;
    std::cout << b.updatePending << ' ' << b.outputCoeffChanged << ' '
              << b.sectionOneCoeffChanged << ' ' << calls << ' '
              << observedArgument << ' ' << observedDirty << ' '
              << observedOutput << ' ' << observedSection << '\n';
  }
}
