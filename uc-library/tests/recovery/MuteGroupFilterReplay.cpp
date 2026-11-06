#include "core/portable/corecomponent.h"
#include "presonus/MuteGroupBase.hpp"
#include <bit>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
class Probe : public Core::Portable::NumericParam {
public:
  Probe(const Core::Portable::ParamInfo &info, float v)
      : NumericParam(info), v(v) {}
  float getValue() const override {
    ++calls;
    return v;
  }
  float v;
  mutable int calls = 0;
};
int main() {
  static_assert(Core::Portable::Component::kTypeID == 1131375984);
  static_assert(Core::Portable::Parameter::kTypeID == 1348563553);
  int save, type, present, name, argument;
  uint32_t bits;
  const char *names[] = {"mute", "Mute", "", "muted", " mute", "m"};
  Presonus::MuteGroupBase::Filter filter;
  while (std::cin >> save >> type >> present >> name >> bits >> argument) {
    Core::Portable::ParamInfo info{};
    std::strncpy(info.name, name < 0 ? "" : names[name], sizeof(info.name) - 1);
    Probe parameter(info, std::bit_cast<float>(bits));
    const Core::Portable::IStorageFilter &provider = filter;
    bool result =
        save ? provider.shouldSave(type, argument ? "ignored" : nullptr,
                                   present ? &parameter : nullptr)
             : provider.shouldLoad(type, argument ? "ignored" : nullptr,
                                   present ? &parameter : nullptr);
    std::cout << result << " " << parameter.calls << "\n";
  }
}
