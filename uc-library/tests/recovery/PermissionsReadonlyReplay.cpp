#include "presonus/mixer/PermissionsComponent.hpp"
#include "presonus/uc/ClientSubscription.hpp"
#include <array>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
using Buffer = Core::CStringBuffer<64>;
Buffer decode(const std::string &hex) {
  if (hex.size() != 128)
    throw std::runtime_error("bad buffer length");
  Buffer value;
  for (unsigned i = 0; i < 64; ++i)
    value.getBuffer()[i] =
        static_cast<char>(std::stoul(hex.substr(i * 2, 2), nullptr, 16));
  if (!std::memchr(value.str(), 0, 64))
    throw std::runtime_error("unterminated input");
  return value;
}
std::string encode(const char *buffer) {
  std::ostringstream text;
  for (unsigned i = 0; i < 64; ++i)
    text << std::hex << std::setfill('0') << std::setw(2)
         << static_cast<unsigned>(static_cast<unsigned char>(buffer[i]));
  return text.str();
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  if (!input)
    return 2;
  std::string line;
  unsigned count = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    std::string op, appHex, deviceHex, displayHex, expected;
    int selected;
    if (!(row >> op >> selected >> appHex >> deviceHex >> displayHex >>
          expected))
      return 3;
    const Buffer app = decode(appHex), device = decode(deviceHex),
                 display = decode(displayHex);
    const Presonus::UC::ClientSubscription client(
        Presonus::UC::ClientSubscription::SourcePortValues{}, app, device,
        display);
    Presonus::Mixer::PermissionsBindings bindings;
    bindings.selectedSnapshot = selected ? &client : nullptr;
    Presonus::Mixer::PermissionsComponent component(bindings);
    std::string actual;
    if (op == "app")
      actual = std::to_string(component.getAppType(client));
    else if (op == "selectedApp")
      actual = std::to_string(component.getSelectedDeviceApp());
    else if (op == "device")
      actual = std::to_string(component.getSelectedDeviceType());
    else if (op == "info") {
      struct Guarded {
        std::array<unsigned char, 16> before;
        Buffer result;
        std::array<unsigned char, 16> after;
      } guarded;
      guarded.before.fill(0xa7);
      guarded.after.fill(0x7a);
      guarded.result = component.createClientInfo(&client);
      for (unsigned i = 0; i < 16; ++i)
        if (guarded.before[i] != 0xa7 || guarded.after[i] != 0x7a)
          return 4;
      actual = encode(guarded.result.str());
    } else
      return 5;
    if (actual != expected || encode(client.sourcePortApp().str()) != appHex ||
        encode(client.sourcePortDevice().str()) != deviceHex ||
        encode(client.sourcePortDisplay().str()) != displayHex ||
        bindings.selectedSnapshot != (selected ? &client : nullptr)) {
      std::cerr << "mismatch " << count << ' ' << op << " actual " << actual
                << " expected " << expected << '\n';
      return 1;
    }
    ++count;
  }
  std::cout
      << "passed " << count
      << " native fixture cases; full 64-byte output, input and guard checks\n";
  return count ? 0 : 6;
}
