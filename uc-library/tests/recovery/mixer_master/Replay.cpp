#include "core/portable/coreparams.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
using namespace Core::Portable;
BEGIN_PARAMINFO(parameters)
PARAM_FLOAT_(5, "cascade", -100, 100, 0, .001, "", "", 0, 0, "Cascade", nullptr)
END_PARAMINFO
int main() {
  Component provider;
  provider.addParameters(parameters, 1);
  auto *parameter = NumericParam::cast(provider.getParameterByTag(5));
  assert(parameter);
  Presonus::Mixer::MixerComponentBase owner;
  owner.cascadeParameters = &provider;
  std::uint32_t bits;
  while (std::cin >> bits) {
    float value;
    std::memcpy(&value, &bits, sizeof value);
    parameter->setValueFast(value);
    std::cout << owner.isMaster() << ' ' << owner.isSlave() << '\n';
    assert(owner.cascadeParameters == &provider);
  }
}
