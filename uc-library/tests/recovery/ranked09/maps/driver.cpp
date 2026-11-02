#include "presonus/DAWTimeInfo.hpp"
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>
std::vector<std::uint8_t> decode(const std::string &text) {
  std::vector<std::uint8_t> bytes;
  if (text == "-")
    return bytes;
  for (std::size_t i = 0; i < text.size(); i += 2)
    bytes.push_back(std::stoul(text.substr(i, 2), nullptr, 16));
  return bytes;
}
int main() {
  std::string kind, query, hex;
  int count;
  while (std::cin >> kind >> count >> query >> hex) {
    auto data = decode(hex), q = decode(query);
    double value;
    std::uint64_t bits = 0;
    for (unsigned i = 0; i < 8; ++i)
      bits |= std::uint64_t(q[i]) << (8 * i);
    std::memcpy(&value, &bits, 8);
    auto before = data;
    const std::uint8_t *result;
    if (kind == "signature")
      result = Presonus::DAWTimeInfo::TimeSignatureMap(data.data(), count)
                   .findItem(value);
    else
      result =
          Presonus::DAWTimeInfo::TempoMap(data.data(), count).findItem(value);
    int index = count <= 0 ? (kind == "signature" ? -2 : -1)
                           : int((result - data.data()) / 24);
    std::cout << std::dec << index << ' ';
    if (result)
      for (unsigned i = 0; i < 24; ++i)
        std::cout << std::hex << std::setw(2) << std::setfill('0')
                  << unsigned(result[i]);
    else
      std::cout << '-';
    std::cout << ' ' << (before == data) << '\n';
  }
}
