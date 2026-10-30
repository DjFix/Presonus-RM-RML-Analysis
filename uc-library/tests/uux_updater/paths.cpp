#include "presonus/uux/FirmwareUpdaterPaths.hpp"
#include "process_boundary.hpp"
#include <array>
#include <cassert>
#include <cstring>
#include <iostream>
int main() {
  fixture::requireProductionMethods();
  static_assert(sizeof(Core::CStringBuffer<256>) == 256);
  unsigned method, length, seed, expected, count = 0;
  while (std::cin >> method >> length >> seed >> expected) {
    assert(method < 2 && length < 256);
    Core::CString256 input;
    std::array<unsigned char, 256> data, unchanged;
    unchanged.fill(0x55);
    for (unsigned i = 0; i < 256; ++i)
      data[i] = ((i + seed) % 255) + 1;
    data[length] = 0;
    std::memcpy(input.getBuffer(), data.data(), 256);
    Presonus::UUX::FirmwareUpdater updater(presonus::uux::PathsSourcePort{});
    using View = presonus::uux::PathView;
    std::memcpy(View::usb(updater).getBuffer(), unchanged.data(), 256);
    std::memcpy(View::url(updater).getBuffer(), unchanged.data(), 256);
    int result = method == 0 ? updater.setUsbImagePath(input)
                             : updater.setUuxUpgradeUrl(input);
    assert(static_cast<unsigned>(result) == expected);
    assert(std::memcmp(input.str(), data.data(), 256) == 0);
    assert(std::memcmp(View::usb(updater).str(),
                       method == 0 ? data.data() : unchanged.data(), 256) == 0);
    assert(std::memcmp(View::url(updater).str(),
                       method == 1 ? data.data() : unchanged.data(), 256) == 0);
    ++count;
  }
  assert(count == 3072);
  std::cout << "PASS original_path_cases=" << count << '\n';
}
