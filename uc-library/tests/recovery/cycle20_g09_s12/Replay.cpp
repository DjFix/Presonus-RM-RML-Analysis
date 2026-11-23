#include "presonus/mixer/FilterFreqFormatter.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main() {
  std::uint32_t valueBits;
  unsigned style;
  int capacity;
  while (std::cin >> valueBits >> style >> capacity) {
    if (style > 255 || capacity < 0 || capacity > 64)
      return 2;
    Presonus::Mixer::FilterFreqFormatter formatter{};
    const Core::Formatter &interface = formatter;
    std::array<unsigned char, 64> output;
    output.fill(0xd9);
    const int object = 7;
    const Core::Formatter::Range range{0.f, 1.f};
    Core::Formatter::Data data{&object, reinterpret_cast<char *>(output.data()),
                               capacity, 0.f, &range};
    std::memcpy(&data.value, &valueBits, sizeof(valueBits));
    interface.print(data);
    if (data.object != &object || data.range != &range ||
        data.size != capacity ||
        data.string != reinterpret_cast<char *>(output.data()))
      throw std::runtime_error("formatter changed the Data context");
    auto scanProbe = data;
    if (interface.scan(scanProbe) ||
        std::memcmp(&scanProbe.value, &data.value, sizeof(data.value)))
      throw std::runtime_error("unexpected portable CCL scan behavior");
    std::memcpy(&valueBits, &data.value, sizeof(valueBits));
    std::cout << valueBits << ' ';
    for (auto value : output)
      std::cout << std::hex << std::setw(2) << std::setfill('0')
                << static_cast<unsigned>(value);
    std::cout << std::dec << '\n';
  }
  return std::cin.eof() ? 0 : 2;
}
