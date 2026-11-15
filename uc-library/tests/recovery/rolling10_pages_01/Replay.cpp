#include "presonus/PageComponent.hpp"
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
class Bindings final : public presonus::page::Bindings {
public:
  void *castOwner(void *, int) const override { std::abort(); }
  const void *currentPage(void *) const override { std::abort(); }
  void stopTextInput(void *, bool) const override { std::abort(); }
  bool isEditingText(void *) const override { std::abort(); }
};
int main() {
  Bindings bindings;
  std::string hex;
  unsigned address;
  while (std::cin >> hex >> address) {
    std::string text;
    if (hex != "-")
      for (std::size_t i = 0; i < hex.size(); i += 2)
        text += static_cast<char>(std::stoul(hex.substr(i, 2), nullptr, 16));
    Presonus::PageComponent first(nullptr, bindings, text.c_str());
    Presonus::PageComponent second(nullptr, bindings, "independent");
    const auto &object = first;
    const char *result = object.getFormName();
    if (result != object.getFormName() || result == second.getFormName())
      return 2;
    std::ostringstream encoded;
    for (const unsigned char *p =
             reinterpret_cast<const unsigned char *>(result);
         *p; ++p)
      encoded << std::hex << std::setw(2) << std::setfill('0') << unsigned(*p);
    std::cout << (encoded.str().empty() ? "-" : encoded.str()) << '\n';
  }
  return std::cin.eof() ? 0 : 3;
}
