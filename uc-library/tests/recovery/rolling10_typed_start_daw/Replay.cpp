#include "presonus/surface/StartPageComponent.hpp"
#include <bit>
#include <cstdint>
#include <iostream>
#include <string>
struct Page : Presonus::Surface::StartPageComponent {
  void add(Core::Portable::Parameter *p) { paramList.add(p); }
};
int main(int argc, char **argv) {
  bool provider = argc > 1 && std::string(argv[1]) == "provider";
  std::uint32_t bits, other;
  while (std::cin >> bits >> other) {
    Page page;
    Core::Portable::ParamInfo a{}, b{};
    a.tag = 1000;
    b.tag = 1001;
    a.defaultValue = std::bit_cast<float>(bits);
    b.defaultValue = std::bit_cast<float>(other);
    page.add(new Core::Portable::NumericParam(b));
    page.add(new Core::Portable::NumericParam(a));
    auto *p = page.getParameterByTag(1000);
    if (!p || !Core::Portable::NumericParam::cast(p))
      return 2;
    const auto before = std::bit_cast<std::uint32_t>(p->getValue());
    if (provider)
      std::cout << p->getTag() << ' ' << before << '\n';
#ifndef PROVIDER_ONLY
    else
      std::cout << page.isDawMode() << '\n';
#endif
    if (std::bit_cast<std::uint32_t>(p->getValue()) != before ||
        std::bit_cast<std::uint32_t>(
            page.getParameterByTag(1001)->getValue()) != other)
      return 3;
  }
}
