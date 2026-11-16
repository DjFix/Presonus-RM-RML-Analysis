#include "core/portable/coreparams.h"
#include "presonus/mixer/AliasMapping.hpp"
#include <cstring>
#include <iostream>
int main() {
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kAlias;
  Core::Portable::AliasParam alias(info);
  Core::Portable::NumericParam parameter(info);
  unsigned cases = 0;
  for (const char *name : {static_cast<const char *>(nullptr), "", "gain",
                           "1234567890123456789012345678901",
                           "1234567890123456789012345678901234567890"})
    for (bool hasAlias : {false, true})
      for (bool hasParameter : {false, true}) {
        Core::Portable::AliasParam *a = hasAlias ? &alias : nullptr;
        Core::Portable::Parameter *p = hasParameter ? &parameter : nullptr;
        Presonus::Mixer::AliasMapping actual(a, p, name);
        Presonus::Mixer::ControlMapping provider(p, name);
        Core::CString32 ccl(name);
        if (actual.alias() != a || actual.parameter() != p ||
            std::strcmp(actual.name(), provider.name()) ||
            std::strcmp(provider.name(), ccl.str()))
          return 1;
        std::cout << hasAlias << " " << hasParameter << " " << actual.name()
                  << "\n";
        ++cases;
      }
  if (cases != 20)
    return 2;
}
