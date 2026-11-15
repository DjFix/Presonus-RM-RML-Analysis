#include "presonus/surface/PageHeaderComponent.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
#include <vector>
int main() {
  using namespace Core::Portable;
  for (int aliases : {0, 1, 3})
    for (const char *initial : {"", "selected"})
      for (bool present : {false, true}) {
        ParamInfo info = {};
        std::strcpy(info.name, "label");
        info.type = ParamInfo::kString;
        StringParam actualLabel(info), providerLabel(info);
        actualLabel.fromString(initial, false);
        providerLabel.fromString(initial, false);
        Presonus::Surface::PageHeaderComponent actual(
            "actual", present ? &actualLabel : nullptr);
        Presonus::MappablePageComponent provider("provider");
        std::vector<AliasParam *> actualAliases, providerAliases;
        for (int i = 0; i < aliases; ++i) {
          auto &a = actual.addMappable(i, "alias");
          a.setOriginal(&actualLabel);
          actualAliases.push_back(&a);
          auto &b = provider.addMappable(i, "alias");
          b.setOriginal(&providerLabel);
          providerAliases.push_back(&b);
        }
        provider.disconnectMappables();
        if (present)
          providerLabel.fromString("", false);
        actual.disconnectMappables();
        char a[32], b[32];
        actualLabel.toString(a, 32);
        providerLabel.toString(b, 32);
        assert(std::strcmp(a, b) == 0);
        for (int i = 0; i < aliases; ++i) {
          assert(actualAliases[i]->getOriginal() == nullptr);
          assert(providerAliases[i]->getOriginal() == nullptr);
        }
      }
  std::cout << "12 actual-provider cases passed\n";
}
