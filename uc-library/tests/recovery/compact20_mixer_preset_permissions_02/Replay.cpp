#include "presonus/mixer/OutputComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
int main() {
  Core::Portable::ParamInfo info{};
  info.tag = 400;
  std::strcpy(info.name, "delay");
  Core::Portable::NumericParam a(info), b(info), c(info), d(info);
  std::array<Core::Portable::Parameter *, 5> parameters{nullptr, &a, &b, &c,
                                                        &d};
  std::array<float, 4> before{a.getValue(), b.getValue(), c.getValue(),
                              d.getValue()};
  presonus::mixer::ChannelState channel{};
  presonus::output_port::Bindings bindings{channel};
  Presonus::Mixer::OutputComponent subject(bindings);
  presonus::output_port::Bindings otherBindings{channel};
  Presonus::Mixer::OutputComponent otherSubject(otherBindings);
  for (unsigned object = 0; object < 2; ++object) {
    auto &activeBindings = object == 0 ? bindings : otherBindings;
    auto &activeSubject = object == 0 ? subject : otherSubject;
    for (unsigned token = 0; token < parameters.size(); ++token) {
      activeBindings.delay = parameters[token];
      if (activeSubject.getDelay() != parameters[token] ||
          activeSubject.getDelay() != activeBindings.delay)
        return 1;
      if (activeBindings.updatePending || activeBindings.outputCoeffChanged ||
          activeBindings.sectionOneCoeffChanged)
        return 2;
      if (std::array<float, 4>{a.getValue(), b.getValue(), c.getValue(),
                               d.getValue()} != before)
        return 3;
      std::cout << object << ' ' << token << ' ' << token << ' ' << 0 << '\n';
    }
  }
}
