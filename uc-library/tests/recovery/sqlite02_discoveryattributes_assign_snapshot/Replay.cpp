#include "presonus/uc/discovery_attributes.hpp"
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string_view>

using Presonus::UC::DiscoveryAttributes;

static void initialize(DiscoveryAttributes &value, std::string_view raw) {
  std::size_t offset = 0;
  const auto nextByte = [&]() {
    if (offset + 2 > raw.size())
      throw std::invalid_argument("Fixture is truncated");
    auto byte = static_cast<unsigned char>(
        std::stoul(std::string(raw.substr(offset, 2)), nullptr, 16));
    offset += 2;
    return byte;
  };
  for (auto &word : value.words) {
    word = 0;
    for (unsigned shift = 0; shift < 32; shift += 8)
      word |= static_cast<std::uint32_t>(nextByte()) << shift;
  }
  for (auto &text : value.strings) {
    char *buffer = text.getBuffer();
    for (int i = 0; i < text.getSize(); ++i)
      buffer[i] = static_cast<char>(nextByte());
  }
  if (offset != raw.size())
    throw std::invalid_argument("Extra bytes in fixture");
}

static void print(const DiscoveryAttributes &value) {
  std::cout << std::hex << std::setfill('0');
  for (auto word : value.words) {
    for (unsigned shift = 0; shift < 32; shift += 8)
      std::cout << std::setw(2) << ((word >> shift) & 0xffU);
  }
  for (const auto &text : value.strings) {
    for (int i = 0; i < text.getSize(); ++i)
      std::cout << std::setw(2)
                << static_cast<unsigned>(
                       static_cast<unsigned char>(text.str()[i]));
  }
  std::cout << '\n';
}

int main(int argc, char **argv) {
  if (argc != 4)
    return 1;
  DiscoveryAttributes src, dst;
  initialize(src, argv[1]);
  initialize(dst, argv[2]);
  const auto &input = std::string_view(argv[3]) == "1" ? dst : src;
  DiscoveryAttributes &result = (dst = input);
  std::cout << (&result == &dst) << '\n';
  print(src);
  print(dst);
}
