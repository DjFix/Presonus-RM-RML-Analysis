#include "presonus/ColorMapping.hpp"
#include "presonus/MappingTable.hpp"
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string>
static void bytes(const char *data) {
  for (int i = 0; i < 32; ++i)
    std::cout << std::hex << std::setw(2) << std::setfill('0')
              << static_cast<unsigned>(static_cast<unsigned char>(data[i]));
  std::cout << std::dec << '\n';
}
int main(int argc, char **argv) {
  for (int index = 1; index < argc;) {
    const std::string mode(argv[index++]);
    if (mode == "color") {
      if (index + 1 >= argc)
        return 2;
      Core::ConstString name(argv[index++]);
      auto result = Presonus::ColorMapping::enumFromString(
          name, static_cast<RGBLedColors>(
                    static_cast<int>(std::stoul(argv[index++]))));
      std::cout << static_cast<std::uint32_t>(result) << '\n';
    } else if (mode == "palette") {
      if (index >= argc)
        return 2;
      const auto raw = std::stoul(argv[index++]);
      Core::Color color(raw & 255, (raw >> 8) & 255, (raw >> 16) & 255,
                        (raw >> 24) & 255);
      const char *name = Presonus::ColorMapping::mapColor(color);
      std::cout << Presonus::ColorMapping::mapColorToEnum(color) << '\n'
                << (name ? name : "") << '\n';
    } else {
      if (index >= argc)
        return 2;
      Core::CString32 page, parameter;
      std::memset(page.getBuffer(), 0xa5, 32);
      std::memcpy(page.getBuffer(), "old-page", 9);
      std::memset(parameter.getBuffer(), 0x5a, 32);
      std::memcpy(parameter.getBuffer(), "old-param", 10);
      const char *input = argv[index++];
      auto result = Presonus::MappingTable::extractPageName(
          mode == "null" ? nullptr : input, page, parameter);
      std::cout << result << '\n'
                << page.str() << '\n'
                << parameter.str() << '\n';
      bytes(page.str());
      bytes(parameter.str());
    }
  }
}
