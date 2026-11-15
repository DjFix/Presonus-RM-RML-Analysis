#include "presonus/surface/MarkerPageComponent.hpp"
#include <bit>
#include <cstdint>
#include <iostream>
#include <string>
struct Page : Presonus::Surface::MarkerPageComponent {
  void add(Core::Portable::Parameter *p) { paramList.add(p); }
  Core::Portable::Parameter *lookup() { return paramList.byTag(1007); }
};
int main(int argc, char **argv) {
  bool provider = argc > 1 && std::string(argv[1]) == "provider";
  unsigned present, bits;
  while (std::cin >> present >> bits) {
    Page page;
    Core::Portable::ParamInfo info{};
    info.tag = 1007;
    info.defaultValue = std::bit_cast<float>(std::uint32_t(bits));
    if (present)
      page.add(new Core::Portable::NumericParam(info, false));
    if (provider) {
      auto *p = page.lookup();
      std::cout << (p ? 1 : 0) << " "
                << (p ? std::bit_cast<std::uint32_t>(p->getValue()) : 0)
                << "\n";
    } else
      std::cout << page.isLocateMode() << "\n";
  }
}
